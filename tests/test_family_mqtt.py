# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_family_mqtt.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The family on a retained MQTT topic: the configuration, the packets, a publish against a stand-in broker and the publisher that sends on a change."""
from __future__ import annotations

import json
import socket
import threading

import pytest

from hydra_umc_cognitive_node.family_mqtt import (
    FamilyPublisher, MqttConfig, MqttConfigError, MqttError, connect_packet, family_payload, load_mqtt_config, parse_mqtt_config, publish, publish_packet,
)

STATUS = {"schema_version": "1.0", "shared_models": {"present": True, "path": "/secret/place/models"}, "all_children_present": True,
          "children": [{"name": "HYDRA-UMC-VLA-ENGINE", "present": True, "version": "0.1.0", "maturity": "functional", "role": "x"}]}


def test_it_is_off_by_default():
    assert MqttConfig().enabled is False
    assert parse_mqtt_config({}).enabled is False
    assert parse_mqtt_config({}).topic == "hydra/cognitive/family"


@pytest.mark.parametrize("bad", [
    [], {"enabled": 1}, {"unknown": 1}, {"broker": "nohost"}, {"broker": "h:99999"}, {"topic": "a/#"}, {"topic": "$SYS/x"}, {"topic": "a/+/b"},
    {"intervalSeconds": 0}, {"timeoutSeconds": True}, {"passwordFile": "p"}, {"enabled": True, "broker": "broker.example:1883"}, {"caFile": ""},
])
def test_a_bad_configuration_is_refused(bad):
    with pytest.raises(MqttConfigError):
        parse_mqtt_config(bad)


def test_a_remote_broker_needs_tls_or_a_plaintext_choice():
    assert parse_mqtt_config({"enabled": True, "broker": "broker.example:8883", "tls": True}).tls
    assert parse_mqtt_config({"enabled": True, "broker": "broker.example:1883", "allowPlaintext": True}).allow_plaintext
    assert parse_mqtt_config({"enabled": True, "broker": "[::1]:1883"}).host_port == ("::1", 1883)


def test_a_configuration_file_is_read(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"enabled": True, "topic": "t/x"}), encoding="utf-8")
    assert load_mqtt_config(str(path)).topic == "t/x"
    with pytest.raises(MqttConfigError):
        load_mqtt_config(str(tmp_path / "missing.json"))


def test_the_packets_are_the_ones_of_mqtt_311():
    assert publish_packet("a/b", b"hi", True) == b"\x31\x07\x00\x03a/bhi"
    assert publish_packet("a/b", b"hi", False)[0] == 0x30
    assert connect_packet("c")[:2] == b"\x10\x0d"
    assert b"user" in connect_packet("c", "user", "pw")
    with pytest.raises(MqttError):
        publish_packet("a/#", b"", True)
    with pytest.raises(MqttError):
        publish_packet("", b"", True)
    assert len(publish_packet("t", b"x" * 300, True)) == 1 + 2 + 2 + 1 + 300


def test_the_payload_names_no_path():
    payload = family_payload(STATUS)
    text = json.dumps(payload)
    assert "secret" not in text and "role" not in text
    assert payload["online"] is True and payload["sharedModelsPresent"] is True and payload["children"][0]["version"] == "0.1.0"
    assert family_payload({}, online=False) == {"schema": "1.0", "online": False}


class _Broker:
    """A broker that accepts one connection per message, answers CONNACK and keeps what was published."""

    def __init__(self, code: int = 0) -> None:
        self.code = code
        self.received: list[bytes] = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                conn.settimeout(2)
                try:
                    conn.recv(1024)
                    conn.sendall(bytes([0x20, 0x02, 0x00, self.code]))
                    data = b""
                    while not data.endswith(b"\xe0\x00"):
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        data += chunk
                    self.received.append(data)
                except OSError:
                    pass

    def close(self) -> None:
        self.sock.close()


def test_a_message_reaches_the_broker_retained():
    broker = _Broker()
    try:
        config = parse_mqtt_config({"enabled": True, "broker": f"127.0.0.1:{broker.port}"})
        publish(config, "hydra/cognitive/family", b'{"a":1}')
        for _ in range(50):
            if broker.received:
                break
            threading.Event().wait(0.05)
        assert broker.received and broker.received[0][0] == 0x31 and b'{"a":1}' in broker.received[0]
    finally:
        broker.close()


def test_a_refusing_broker_and_a_missing_broker_are_errors():
    broker = _Broker(code=5)
    try:
        config = parse_mqtt_config({"enabled": True, "broker": f"127.0.0.1:{broker.port}"})
        with pytest.raises(MqttError, match="refused"):
            publish(config, "t", b"x")
    finally:
        broker.close()
    with pytest.raises(MqttError, match="cannot reach"):
        publish(parse_mqtt_config({"enabled": True, "broker": "127.0.0.1:1", "timeoutSeconds": 0.5}), "t", b"x")


def test_credentials_that_cannot_be_read_are_an_error(tmp_path):
    config = parse_mqtt_config({"enabled": True, "usernameFile": str(tmp_path / "missing")})
    with pytest.raises(MqttError, match="credential"):
        publish(config, "t", b"x")


def test_the_publisher_sends_on_a_change_and_on_the_refresh_only():
    now = [0.0]
    status = [STATUS]
    sent: list[tuple[str, bytes, bool]] = []
    config = parse_mqtt_config({"enabled": True, "refreshSeconds": 60})
    publisher = FamilyPublisher(config, lambda probe: status[0], lambda c, topic, data, retain: sent.append((topic, data, retain)), clock=lambda: now[0])
    assert publisher.step() is True and publisher.step() is False
    now[0] = 30
    assert publisher.step() is False
    now[0] = 61
    assert publisher.step() is True
    status[0] = dict(STATUS, all_children_present=False)
    assert publisher.step() is True
    assert len(sent) == 3 and all(topic == "hydra/cognitive/family" and retain for topic, _, retain in sent)
    publisher.stop()
    assert json.loads(sent[-1][1]) == {"online": False, "schema": "1.0"}


def test_a_failing_broker_is_counted_and_the_next_look_tries_again():
    calls: list[int] = []

    def send(config, topic, data, retain):
        calls.append(1)
        if len(calls) == 1:
            raise MqttError("down")

    publisher = FamilyPublisher(parse_mqtt_config({"enabled": True}), lambda probe: STATUS, send)
    assert publisher.step() is False and publisher.failed == 1 and publisher.last_error == "down"
    assert publisher.step() is True and publisher.stats()["published"] == 1 and publisher.last_error == ""


def test_an_unreadable_family_is_counted():
    def snapshot(probe):
        raise ValueError("bad manifest")

    publisher = FamilyPublisher(parse_mqtt_config({"enabled": True}), snapshot, lambda *a: None)
    assert publisher.step() is False and "bad manifest" in publisher.last_error
