# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/family_mqtt.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The state of the family on a retained MQTT topic, off by default.

With ``--mqtt-config`` and ``"enabled": true`` the node publishes the same readiness it answers on ``GET /family-status`` (what is installed and, when
``probe`` is on, what answers) to one retained topic (``hydra/cognitive/family`` by default), so the Studio, the Suite and the phones read it without asking
the node. It publishes when the content changes and, at most every ``refreshSeconds``, once more so that a client that subscribes late and a broker that lost
its retained messages both recover. When the node stops it publishes ``{"online": false}`` on the same topic.

The payload names no path, address or token. The broker is reached with the smallest MQTT 3.1.1 publisher that does the job (connect, publish at QoS 0,
disconnect), the same as the watchdog of the ecosystem: no dependency. A broker that is not on this machine needs TLS, or ``allowPlaintext`` set on purpose.
"""
from __future__ import annotations

import json
import socket
import ssl
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .access import is_loopback

MAX_PACKET = 268435455
_TOPIC_BAD = ("#", "+", "\x00")
SCHEMA = "1.0"


class MqttConfigError(ValueError):
    """The configuration cannot be used; the message says which key and why."""


class MqttError(OSError):
    """The broker could not be reached or refused the message."""


@dataclass(frozen=True)
class MqttConfig:
    enabled: bool = False
    broker: str = "127.0.0.1:1883"
    tls: bool = False
    ca_file: str | None = None
    client_id: str = "hydra-umc-cognitive-node"
    username_file: str | None = None
    password_file: str | None = None
    allow_plaintext: bool = False
    timeout_seconds: float = 5.0
    topic: str = "hydra/cognitive/family"
    interval_seconds: float = 10.0
    refresh_seconds: float = 300.0
    probe: bool = False

    @property
    def host_port(self) -> tuple[str, int]:
        host, _, port = self.broker.rpartition(":")
        return host.strip("[]"), int(port)


def parse_mqtt_config(raw: object) -> MqttConfig:
    if not isinstance(raw, dict):
        raise MqttConfigError("the configuration must be a JSON object")
    allowed = {"enabled", "broker", "tls", "caFile", "clientId", "usernameFile", "passwordFile", "allowPlaintext", "timeoutSeconds", "topic", "intervalSeconds",
               "refreshSeconds", "probe"}
    unknown = set(raw) - allowed
    if unknown:
        raise MqttConfigError(f"unknown key {sorted(unknown)[0]}")
    defaults = MqttConfig()

    def boolean(key: str, default: bool) -> bool:
        value = raw.get(key, default)
        if not isinstance(value, bool):
            raise MqttConfigError(f"{key} must be true or false")
        return value

    def text(key: str, default: str | None) -> str | None:
        value = raw.get(key, default)
        if value is not None and (not isinstance(value, str) or not value):
            raise MqttConfigError(f"{key} must be a non-empty text")
        return value

    def seconds(key: str, default: float, low: float, high: float) -> float:
        value = raw.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise MqttConfigError(f"{key} must be a number from {low:g} to {high:g}")
        return float(value)

    broker = text("broker", defaults.broker) or defaults.broker
    host, _, port = broker.rpartition(":")
    if not host or not port.isdigit() or not 0 < int(port) < 65536:
        raise MqttConfigError("broker must be host:port")
    topic = text("topic", defaults.topic) or defaults.topic
    if any(c in topic for c in _TOPIC_BAD) or topic.startswith("$") or len(topic.encode("utf-8")) > 256:
        raise MqttConfigError("topic must have no wildcards, no NUL, not start with $ and be at most 256 bytes")
    config = MqttConfig(
        enabled=boolean("enabled", False), broker=broker, tls=boolean("tls", False), ca_file=text("caFile", None),
        client_id=text("clientId", defaults.client_id) or defaults.client_id, username_file=text("usernameFile", None), password_file=text("passwordFile", None),
        allow_plaintext=boolean("allowPlaintext", False), timeout_seconds=seconds("timeoutSeconds", 5.0, 0.5, 60.0), topic=topic,
        interval_seconds=seconds("intervalSeconds", 10.0, 1.0, 3600.0), refresh_seconds=seconds("refreshSeconds", 300.0, 10.0, 86400.0), probe=boolean("probe", False))
    if config.password_file and not config.username_file:
        raise MqttConfigError("passwordFile needs usernameFile")
    if config.enabled and not config.tls and not config.allow_plaintext and not is_loopback(host):
        raise MqttConfigError("a broker that is not on this machine needs tls, or allowPlaintext set on purpose")
    return config


def load_mqtt_config(path: str) -> MqttConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MqttConfigError(f"cannot read {path}: {error}") from error
    return parse_mqtt_config(raw)


def _length(n: int) -> bytes:
    if not 0 <= n <= MAX_PACKET:
        raise MqttError("an MQTT packet cannot be this long")
    out = bytearray()
    while True:
        digit, n = n % 128, n // 128
        out.append(digit | 0x80 if n else digit)
        if not n:
            return bytes(out)


def _string(value: str) -> bytes:
    data = value.encode("utf-8")
    if len(data) > 65535:
        raise MqttError("an MQTT string cannot be this long")
    return struct.pack(">H", len(data)) + data


def connect_packet(client_id: str, username: str = "", password: str = "") -> bytes:
    flags = 0x02
    payload = _string(client_id)
    if username:
        flags |= 0x80
        payload += _string(username)
        if password:
            flags |= 0x40
            payload += _string(password)
    body = b"\x00\x04MQTT\x04" + bytes([flags]) + b"\x00\x1e" + payload
    return b"\x10" + _length(len(body)) + body


def publish_packet(topic: str, payload: bytes, retain: bool) -> bytes:
    if not topic or any(c in topic for c in _TOPIC_BAD):
        raise MqttError("a topic to publish to has no wildcards and is not empty")
    body = _string(topic) + payload
    return bytes([0x31 if retain else 0x30]) + _length(len(body)) + body


def _secret(path: str | None) -> str:
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise MqttError(f"cannot read a credential file: {error}") from error


def publish(config: MqttConfig, topic: str, payload: bytes, retain: bool = True) -> None:
    """Connect, publish one message at QoS 0 and disconnect. Raises ``MqttError``."""
    packet = publish_packet(topic, payload, retain)
    connect = connect_packet(config.client_id, _secret(config.username_file), _secret(config.password_file))
    host, port = config.host_port
    try:
        raw = socket.create_connection((host, port), timeout=config.timeout_seconds)
    except OSError as error:
        raise MqttError(f"cannot reach the broker at {config.broker}: {error}") from error
    conn: Any = raw
    try:
        if config.tls:
            context = ssl.create_default_context(cafile=config.ca_file) if config.ca_file else ssl.create_default_context()
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            conn = context.wrap_socket(raw, server_hostname=host)
        conn.settimeout(config.timeout_seconds)
        conn.sendall(connect)
        reply = b""
        while len(reply) < 4:
            chunk = conn.recv(4 - len(reply))
            if not chunk:
                raise MqttError("the broker closed the connection before CONNACK")
            reply += chunk
        if reply[0] != 0x20 or reply[1] != 0x02:
            raise MqttError("the broker did not answer CONNECT with CONNACK")
        if reply[3] != 0:
            raise MqttError(f"the broker refused the connection (return code {reply[3]})")
        conn.sendall(packet + b"\xe0\x00")
    except OSError as error:
        if isinstance(error, MqttError):
            raise
        raise MqttError(f"MQTT exchange with {config.broker} failed: {error}") from error
    finally:
        try:
            conn.close()
        except OSError:
            pass


def family_payload(status: dict[str, Any], online: bool = True) -> dict[str, Any]:
    """What goes on the topic: the family status of the API without the path of the models, and the verdicts only."""
    if not online:
        return {"schema": SCHEMA, "online": False}
    models = status.get("shared_models") or {}
    children = []
    for child in status.get("children", []):
        entry: dict[str, Any] = {k: child.get(k) for k in ("name", "present", "version", "maturity")}
        health = child.get("health")
        if isinstance(health, dict):
            entry["health"] = {k: health.get(k) for k in ("reachable", "healthy", "http_status", "latency_ms")}
        children.append(entry)
    out: dict[str, Any] = {"schema": SCHEMA, "online": True, "sharedModelsPresent": bool(models.get("present")), "children": children,
                           "allChildrenPresent": bool(status.get("all_children_present"))}
    if "all_children_healthy" in status:
        out["allChildrenHealthy"] = bool(status["all_children_healthy"])
    return out


class FamilyPublisher:
    """Publishes the family on a thread; ``snapshot`` returns the status dict (the one of ``GET /family-status``)."""

    def __init__(self, config: MqttConfig, snapshot: Callable[[bool], dict[str, Any]], send: Callable[[MqttConfig, str, bytes, bool], None] = publish,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.config = config
        self._snapshot = snapshot
        self._send = send
        self._clock = clock
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last: bytes | None = None
        self._last_at = 0.0
        self.published = 0
        self.failed = 0
        self.last_error = ""

    def _publish(self, payload: dict[str, Any]) -> bool:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            self._send(self.config, self.config.topic, data, True)
        except OSError as error:
            self.failed += 1
            self.last_error = str(error)[:200]
            return False
        self.published += 1
        self.last_error = ""
        self._last, self._last_at = data, self._clock()
        return True

    def step(self) -> bool:
        """One look: publishes when the content changed or the refresh time passed. Returns True when a message went out."""
        try:
            payload = family_payload(self._snapshot(self.config.probe))
        except (OSError, ValueError) as error:
            self.failed += 1
            self.last_error = f"cannot read the family: {error}"[:200]
            return False
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if data == self._last and self._clock() - self._last_at < self.config.refresh_seconds:
            return False
        return self._publish(payload)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.step()
            self._stop.wait(self.config.interval_seconds)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="family-mqtt", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.config.timeout_seconds + 1)
        self._publish(family_payload({}, online=False))

    def stats(self) -> dict[str, Any]:
        return {"topic": self.config.topic, "published": self.published, "failed": self.failed, "lastError": self.last_error}
