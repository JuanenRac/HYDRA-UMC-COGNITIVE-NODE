# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_family_mqtt_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The edges of the family publisher: the keys of the configuration that are refused, packets over the size of the standard, credential files that are not
there, a broker that is not there, answers that are not CONNACK, a broker that hangs up half way, and a publisher whose snapshot or broker fails."""
from __future__ import annotations

import socket
import threading
from pathlib import Path

import pytest

from hydra_umc_cognitive_node import family_mqtt as fm


def _one_shot_broker(reply: bytes) -> tuple[int, threading.Thread]:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    def serve() -> None:
        connection, _ = listener.accept()
        with connection, listener:
            connection.settimeout(2)
            try:
                connection.recv(256)
                if reply:
                    connection.sendall(reply)
            except OSError:
                pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return listener.getsockname()[1], thread


def _config(port: int, **over) -> fm.MqttConfig:
    return fm.MqttConfig(enabled=True, broker=f"127.0.0.1:{port}", timeout_seconds=1.0, **over)


@pytest.mark.parametrize("raw", [
    [],
    {"unknown": 1},
    {"enabled": "yes"},
    {"broker": "nohostport"},
    {"broker": "host:0"},
    {"broker": "host:70000"},
    {"broker": ""},
    {"topic": "a/#"},
    {"topic": "$SYS/x"},
    {"topic": "t" * 300},
    {"timeoutSeconds": 0.1},
    {"timeoutSeconds": True},
    {"intervalSeconds": 0},
    {"refreshSeconds": 5},
    {"passwordFile": "/some/file"},
    {"enabled": True, "broker": "broker.example.com:1883"},
])
def test_a_bad_configuration_is_refused_with_the_key_that_is_wrong(raw):
    with pytest.raises(fm.MqttConfigError):
        fm.parse_mqtt_config(raw)


def test_a_broker_off_this_machine_is_accepted_with_tls_or_a_stated_choice():
    assert fm.parse_mqtt_config({"enabled": True, "broker": "broker.example.com:8883", "tls": True}).tls is True
    assert fm.parse_mqtt_config({"enabled": True, "broker": "broker.example.com:1883", "allowPlaintext": True}).allow_plaintext is True
    assert fm.parse_mqtt_config({"broker": "[::1]:1883"}).host_port == ("::1", 1883)


def test_a_configuration_file_that_is_not_there_or_not_json_is_refused(tmp_path: Path):
    with pytest.raises(fm.MqttConfigError, match="cannot read"):
        fm.load_mqtt_config(str(tmp_path / "missing.json"))
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(fm.MqttConfigError, match="cannot read"):
        fm.load_mqtt_config(str(broken))
    good = tmp_path / "good.json"
    good.write_text('{"enabled": true, "topic": "plant/family"}', encoding="utf-8")
    assert fm.load_mqtt_config(str(good)).topic == "plant/family"


def test_lengths_and_strings_over_the_standard_are_refused():
    with pytest.raises(fm.MqttError):
        fm._length(-1)
    with pytest.raises(fm.MqttError):
        fm._length(fm.MAX_PACKET + 1)
    assert fm._length(fm.MAX_PACKET) == b"\xff\xff\xff\x7f"
    with pytest.raises(fm.MqttError):
        fm._string("x" * 65536)


def test_connect_flags_follow_the_credentials_and_a_password_needs_a_user():
    flag = lambda packet: packet[packet.index(b"MQTT") + 5]  # noqa: E731
    assert flag(fm.connect_packet("c")) == 0x02
    assert flag(fm.connect_packet("c", "user")) == 0x82
    assert flag(fm.connect_packet("c", "user", "secret")) == 0xC2
    assert flag(fm.connect_packet("c", "", "secret")) == 0x02


@pytest.mark.parametrize("topic", ["", "a/#", "a/+", "a\x00"])
def test_a_topic_that_is_empty_or_has_a_wildcard_is_never_built(topic):
    with pytest.raises(fm.MqttError):
        fm.publish_packet(topic, b"x", True)


def test_a_credential_file_that_is_not_there_is_an_mqtt_error(tmp_path: Path):
    assert fm._secret(None) == "" and fm._secret("") == ""
    with pytest.raises(fm.MqttError, match="credential"):
        fm._secret(str(tmp_path / "nope"))
    (tmp_path / "pw").write_text("  secret\n", encoding="utf-8")
    assert fm._secret(str(tmp_path / "pw")) == "secret"
    (tmp_path / "bin").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(fm.MqttError):
        fm._secret(str(tmp_path / "bin"))


def test_a_broker_that_is_not_there_is_an_mqtt_error():
    with socket.socket() as holder:
        holder.bind(("127.0.0.1", 0))
        port = holder.getsockname()[1]
    with pytest.raises(fm.MqttError, match="cannot reach"):
        fm.publish(_config(port), "a/b", b"x")


def test_an_answer_that_is_not_a_connack_is_refused():
    port, thread = _one_shot_broker(b"\x30\x02\x00\x00")
    with pytest.raises(fm.MqttError, match="did not answer CONNECT"):
        fm.publish(_config(port), "a/b", b"x")
    thread.join(timeout=3)


@pytest.mark.parametrize("code", [1, 4, 5])
def test_every_refusal_code_of_the_broker_is_reported_with_its_number(code):
    port, thread = _one_shot_broker(bytes([0x20, 0x02, 0x00, code]))
    with pytest.raises(fm.MqttError, match=f"return code {code}"):
        fm.publish(_config(port), "a/b", b"x")
    thread.join(timeout=3)


def test_a_broker_that_hangs_up_before_the_connack_is_an_mqtt_error():
    port, thread = _one_shot_broker(b"")
    with pytest.raises(fm.MqttError, match="before CONNACK"):
        fm.publish(_config(port), "a/b", b"x")
    thread.join(timeout=3)


def test_tls_against_a_broker_that_speaks_plain_text_is_an_mqtt_error():
    port, thread = _one_shot_broker(b"not tls at all")
    with pytest.raises(fm.MqttError):
        fm.publish(_config(port, tls=True), "a/b", b"x")
    thread.join(timeout=3)


def test_the_payload_of_a_family_without_models_or_health_and_the_offline_payload():
    assert fm.family_payload({}, online=False) == {"schema": "1.0", "online": False}
    payload = fm.family_payload({"children": [{"name": "A", "present": True, "version": "1", "maturity": "alpha", "health": "bad"}]})
    assert payload["children"] == [{"name": "A", "present": True, "version": "1", "maturity": "alpha"}]
    assert payload["sharedModelsPresent"] is False and payload["allChildrenPresent"] is False and "allChildrenHealthy" not in payload
    assert fm.family_payload({"all_children_healthy": 1})["allChildrenHealthy"] is True


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_the_publisher_sends_on_a_change_or_after_the_refresh_time_and_counts_its_failures():
    sent: list[bytes] = []
    state = {"fail": False}

    def send(config, topic, payload, retain):
        if state["fail"]:
            raise fm.MqttError("broker down")
        sent.append(payload)

    clock = _Clock()
    config = fm.MqttConfig(enabled=True, refresh_seconds=100.0)
    snapshot = {"children": []}
    publisher = fm.FamilyPublisher(config, lambda probe: snapshot, send=send, clock=clock)
    assert publisher.step() is True and len(sent) == 1
    assert publisher.step() is False and len(sent) == 1  # nothing changed, nothing is due
    clock.now = 101.0
    assert publisher.step() is True and len(sent) == 2  # the refresh time passed
    snapshot["all_children_present"] = True
    assert publisher.step() is True and len(sent) == 3  # the content changed
    state["fail"] = True
    snapshot["all_children_present"] = False
    assert publisher.step() is False
    assert publisher.stats() == {"topic": config.topic, "published": 3, "failed": 1, "lastError": "broker down"}
    state["fail"] = False
    assert publisher.step() is True and publisher.stats()["lastError"] == ""


def test_a_snapshot_that_cannot_be_read_is_counted_and_never_stops_the_publisher():
    def broken(probe):
        raise OSError("the workspace is gone")

    publisher = fm.FamilyPublisher(fm.MqttConfig(enabled=True), broken, send=lambda *a: None)
    assert publisher.step() is False
    assert publisher.failed == 1 and publisher.last_error.startswith("cannot read the family")


def test_stopping_the_publisher_leaves_an_offline_message():
    sent: list[bytes] = []
    publisher = fm.FamilyPublisher(fm.MqttConfig(enabled=True, interval_seconds=1.0, timeout_seconds=0.5), lambda probe: {}, send=lambda c, t, p, r: sent.append(p))
    publisher.start()
    publisher.stop()
    assert sent and sent[-1] == b'{"online":false,"schema":"1.0"}'
