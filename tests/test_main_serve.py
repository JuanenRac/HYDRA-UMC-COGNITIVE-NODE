# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_main_serve.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The start of the service (`serve`): what it builds from each configuration file, what stops it before it listens (exit 2), what it says, and that it always
stops the publisher and closes the server. The server and the optional parts are stand-ins, so nothing listens and nothing is published."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from hydra_umc_cognitive_node import main as cognitive_main


class FakeServer:
    instances: list["FakeServer"] = []

    def __init__(self, address, workspace, repo_root, models_dir, token, max_threads, narrator, autonomy, scheduler, publisher) -> None:
        self.address, self.token, self.narrator, self.autonomy, self.scheduler, self.publisher = address, token, narrator, autonomy, scheduler, publisher
        self.closed, self.served, self.interrupt = False, False, True
        self.identity_key = None
        self.health_open = None
        FakeServer.instances.append(self)

    def serve_forever(self) -> None:
        self.served = True
        if self.interrupt:
            raise KeyboardInterrupt

    def server_close(self) -> None:
        self.closed = True


class FakePublisher:
    def __init__(self, config, snapshot) -> None:
        self.config, self.snapshot, self.started, self.stopped = config, snapshot, False, False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


@pytest.fixture(autouse=True)
def stand_ins(monkeypatch):
    FakeServer.instances = []
    monkeypatch.setattr(cognitive_main, "CognitiveNodeServer", FakeServer)
    monkeypatch.setattr(cognitive_main, "FamilyPublisher", FakePublisher)
    monkeypatch.setattr(cognitive_main, "health_open_requested", lambda flag: bool(flag))


def serve(**options) -> int:
    defaults = dict(addr="127.0.0.1", port=0, workspace=Path("."))
    return cognitive_main._run_serve(**{**defaults, **options})


def test_a_plain_start_listens_says_so_and_closes_the_server(capsys) -> None:
    assert serve() == 0
    out = capsys.readouterr().out
    assert "HTTP API listening on 127.0.0.1:0" in out and "no token" in out
    assert "GET /family-status, GET /stats" in out
    assert "shutting down" in out
    server = FakeServer.instances[0]
    assert server.served and server.closed and server.health_open is False


def test_the_health_flag_is_passed_on(capsys) -> None:
    serve(health_open=True)
    assert FakeServer.instances[0].health_open is True


def test_a_token_is_announced_and_given_to_the_server(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cognitive_main, "load_token", lambda path: "t" * 32)
    serve(token_file="token")
    assert "Bearer token required except on /stats" in capsys.readouterr().out
    assert FakeServer.instances[0].token == "t" * 32


def test_an_identity_key_replaces_the_warning_and_is_given_to_the_server(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cognitive_main, "identity_key_from", lambda path: b"k" * 40)
    serve(addr="0.0.0.0", identity_key_file="key")
    captured = capsys.readouterr()
    assert "tokens of HYDRA-UMC-SERVER accepted" in captured.out
    assert "warning" not in captured.err
    assert FakeServer.instances[0].identity_key == b"k" * 40


def test_an_open_address_without_a_token_warns(capsys) -> None:
    serve(addr="0.0.0.0")
    assert "warning" in capsys.readouterr().err


def test_a_bad_configuration_stops_before_listening_with_exit_2(monkeypatch, capsys) -> None:
    def refuse(path):
        raise ValueError("the key file is too short")

    monkeypatch.setattr(cognitive_main, "identity_key_from", refuse)
    assert serve(identity_key_file="key") == 2
    assert "too short" in capsys.readouterr().err
    assert FakeServer.instances == []


def test_the_language_model_needs_its_consumer_in_the_npu_budget(monkeypatch, capsys) -> None:
    npu = SimpleNamespace(enabled=True, consumers=("vision",), slots=1)
    monkeypatch.setattr(cognitive_main, "load_npu_config", lambda path: npu)
    monkeypatch.setattr(cognitive_main, "NpuScheduler", lambda config: SimpleNamespace(config=config))
    monkeypatch.setattr(cognitive_main, "load_llm_config", lambda path: SimpleNamespace(enabled=True))
    assert serve(npu_config="npu.json", llm_config="llm.json") == 2
    assert 'no consumer "llm"' in capsys.readouterr().err


def test_the_language_model_and_the_npu_budget_are_announced(monkeypatch, capsys) -> None:
    npu = SimpleNamespace(enabled=True, consumers=("llm",), slots=2)
    monkeypatch.setattr(cognitive_main, "load_npu_config", lambda path: npu)
    monkeypatch.setattr(cognitive_main, "NpuScheduler", lambda config: SimpleNamespace(config=config))
    monkeypatch.setattr(cognitive_main, "load_llm_config", lambda path: SimpleNamespace(enabled=True))
    monkeypatch.setattr(cognitive_main, "make_backend", lambda config: SimpleNamespace(name="simulator"))
    monkeypatch.setattr(cognitive_main, "Narrator", lambda config, backend, scheduler: SimpleNamespace(backend=backend))
    serve(npu_config="npu.json", llm_config="llm.json")
    out = capsys.readouterr().out
    assert "POST /narrative (language model: simulator)" in out
    assert "2 slot(s)" in out
    assert "language model is a SIMULATOR" in out


def test_a_configuration_that_is_switched_off_builds_nothing(monkeypatch) -> None:
    monkeypatch.setattr(cognitive_main, "load_npu_config", lambda path: SimpleNamespace(enabled=False))
    monkeypatch.setattr(cognitive_main, "load_llm_config", lambda path: SimpleNamespace(enabled=False))
    monkeypatch.setattr(cognitive_main, "load_autonomy_config", lambda path: SimpleNamespace(enabled=False))
    monkeypatch.setattr(cognitive_main, "load_mqtt_config", lambda path: SimpleNamespace(enabled=False))
    assert serve(npu_config="a", llm_config="b", autonomy_config="c", mqtt_config="d") == 0
    server = FakeServer.instances[0]
    assert (server.narrator, server.autonomy, server.scheduler, server.publisher) == (None, None, None, None)


def test_the_autonomy_policy_off_loopback_needs_a_credential(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cognitive_main, "load_autonomy_config", lambda path: SimpleNamespace(enabled=True))
    assert serve(addr="0.0.0.0", autonomy_config="autonomy.json") == 2
    assert "needs a bearer token" in capsys.readouterr().err
    assert FakeServer.instances == []


def test_the_autonomy_policy_on_loopback_is_announced(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cognitive_main, "load_autonomy_config", lambda path: SimpleNamespace(enabled=True))
    monkeypatch.setattr(cognitive_main, "AutonomyPolicy", lambda config: SimpleNamespace(config=config))
    serve(autonomy_config="autonomy.json")
    assert "autonomy policy on" in capsys.readouterr().out
    assert FakeServer.instances[0].autonomy is not None


def test_the_publisher_is_started_and_always_stopped(monkeypatch, capsys) -> None:
    created: list[FakePublisher] = []

    def make(config, snapshot):
        publisher = FakePublisher(config, snapshot)
        created.append(publisher)
        return publisher

    monkeypatch.setattr(cognitive_main, "FamilyPublisher", make)
    monkeypatch.setattr(cognitive_main, "load_mqtt_config", lambda path: SimpleNamespace(enabled=True, topic="hydra/cognitive", broker="broker.local"))
    serve(mqtt_config="mqtt.json")
    assert created[0].started and created[0].stopped
    assert "retained topic hydra/cognitive on broker.local" in capsys.readouterr().out


def test_the_publisher_snapshot_reads_the_family(monkeypatch) -> None:
    created: list[FakePublisher] = []
    monkeypatch.setattr(cognitive_main, "FamilyPublisher", lambda config, snapshot: created.append(FakePublisher(config, snapshot)) or created[-1])
    monkeypatch.setattr(cognitive_main, "load_mqtt_config", lambda path: SimpleNamespace(enabled=True, topic="t", broker="b"))
    monkeypatch.setattr(cognitive_main, "check_family_status", lambda workspace: [])
    monkeypatch.setattr(cognitive_main, "check_shared_models", lambda root, models: SimpleNamespace(present=True, path="models", to_dict=lambda: {}))
    monkeypatch.setattr(cognitive_main, "family_status_to_dict", lambda statuses, models, health: {"children": len(statuses), "health": health})
    monkeypatch.setattr(cognitive_main, "probe_family", lambda workspace: [])
    serve(mqtt_config="mqtt.json")
    snapshot = created[0].snapshot
    assert snapshot(False) == {"children": 0, "health": None}
    assert snapshot(True) == {"children": 0, "health": {}}


def test_the_server_is_closed_even_when_serving_fails(monkeypatch) -> None:
    class Failing(FakeServer):
        def serve_forever(self) -> None:
            raise OSError("socket error")

    monkeypatch.setattr(cognitive_main, "CognitiveNodeServer", Failing)
    with pytest.raises(OSError):
        serve()
    assert FakeServer.instances[0].closed


def test_the_command_line_routes_serve_to_the_start(monkeypatch) -> None:
    seen = {}
    monkeypatch.setattr(cognitive_main, "_run_serve", lambda *args, **kwargs: seen.update(args=args, kwargs=kwargs) or 0)
    assert cognitive_main.main(["serve", "--port", "0", "--health-open"]) == 0
    assert seen["kwargs"]["health_open"] is True
    assert seen["args"][1] == 0


def test_the_family_versions_command_prints_a_line_per_child(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cognitive_main, "check_family_status", lambda workspace: ["a", "b"])
    monkeypatch.setattr(cognitive_main, "env_versions", lambda statuses: [f"child-{s}" for s in statuses])
    assert cognitive_main.main(["family-versions"]) == 0
    assert capsys.readouterr().out.split() == ["child-a", "child-b"]


def test_without_a_command_the_identity_is_printed(capsys) -> None:
    assert cognitive_main.main([]) == 0
    assert capsys.readouterr().out.strip()
