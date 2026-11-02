# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_autonomy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The autonomy policy: off by default, the level a source is granted, the confirmation of a person, the audit chain and the routes."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from hydra_umc_cognitive_node.api import CognitiveNodeServer
from hydra_umc_cognitive_node.autonomy import (
    LANGUAGES, REASONS, AutonomyConfig, AutonomyConfigError, AutonomyPolicy, AutonomyRequestError, load_autonomy_config, parse_autonomy_config, verify_chain,
)

ASK = {"source": "voice-ui", "kind": "intent", "actionId": "move-1", "level": "execute_with_confirmation"}


def _policy(sources=None, **over) -> AutonomyPolicy:
    return AutonomyPolicy(AutonomyConfig(enabled=True, sources=sources or {"voice-ui": "execute_with_confirmation", "vla-engine": "propose"}, **over))


def test_it_is_off_by_default():
    assert AutonomyConfig().enabled is False
    assert parse_autonomy_config({}).enabled is False
    assert parse_autonomy_config({}).default_level == "inform"


@pytest.mark.parametrize("bad", [
    [], {"enabled": 1}, {"defaultLevel": "execute"}, {"unknown": 1}, {"sources": []}, {"sources": {"a b": "inform"}}, {"sources": {"a": "root"}},
    {"auditFile": ""}, {"auditMaxBytes": 10}, {"auditMemory": 0}, {"auditMemory": True},
])
def test_a_bad_configuration_is_refused(bad):
    with pytest.raises(AutonomyConfigError):
        parse_autonomy_config(bad)


def test_a_configuration_file_is_read(tmp_path):
    path = tmp_path / "a.json"
    path.write_text(json.dumps({"enabled": True, "sources": {"vla-engine": "propose"}}), encoding="utf-8")
    assert load_autonomy_config(str(path)).sources == {"vla-engine": "propose"}
    with pytest.raises(AutonomyConfigError):
        load_autonomy_config(str(tmp_path / "missing.json"))


def test_a_source_gets_at_most_its_level():
    policy = _policy()
    answer = policy.evaluate(dict(ASK, source="vla-engine"))
    assert answer["decision"] == "deny" and answer["reason"] == "level_limited" and answer["grantedLevel"] == "propose"
    assert policy.evaluate(dict(ASK, source="vla-engine", level="propose"))["decision"] == "allow"
    assert policy.evaluate(dict(ASK, source="vla-engine", level="inform"))["decision"] == "allow"


def test_an_unknown_source_may_only_inform():
    policy = _policy()
    assert policy.evaluate(dict(ASK, source="new-service", level="propose"))["reason"] == "unknown_source_inform_only"
    assert policy.evaluate(dict(ASK, source="new-service", level="inform"))["decision"] == "allow"


def test_execution_needs_the_confirmation_of_a_person():
    policy = _policy()
    assert policy.evaluate(ASK)["decision"] == "needs_confirmation"
    assert policy.evaluate(dict(ASK, humanConfirmed=False))["decision"] == "needs_confirmation"
    assert policy.evaluate(dict(ASK, humanConfirmed=True))["decision"] == "allow"


def test_the_message_is_in_the_language_asked():
    policy = _policy()
    for language in LANGUAGES:
        answer = policy.evaluate(dict(ASK, language=language))
        assert answer["message"] == REASONS["needs_confirmation"][language] and answer["language"] == language
    assert all(set(texts) == set(LANGUAGES) and all(texts.values()) for texts in REASONS.values())


@pytest.mark.parametrize("bad", [
    [], {}, dict(ASK, extra=1), dict(ASK, source="a b"), dict(ASK, level="root"), dict(ASK, humanConfirmed="yes"), dict(ASK, language="xx"), dict(ASK, actionId=7),
])
def test_a_malformed_question_is_refused(bad):
    with pytest.raises(AutonomyRequestError):
        _policy().evaluate(bad)


def test_every_decision_is_audited_in_a_chain(tmp_path):
    log = tmp_path / "audit" / "autonomy.jsonl"
    policy = _policy(audit_file=str(log))
    first = policy.evaluate(ASK)
    policy.evaluate(dict(ASK, humanConfirmed=True))
    policy.evaluate(dict(ASK, source="x"))
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 and json.loads(lines[0])["hash"] == first["auditHash"]
    assert verify_chain(lines) == 3
    tampered = lines[:]
    tampered[1] = tampered[1].replace('"decision":"allow"', '"decision":"deny"')
    with pytest.raises(ValueError, match="line 2"):
        verify_chain(tampered)
    with pytest.raises(ValueError):
        verify_chain([lines[0], lines[2]])


def test_the_chain_continues_after_a_restart_and_a_rotation(tmp_path):
    log = tmp_path / "a.jsonl"
    first = _policy(audit_file=str(log)).evaluate(ASK)
    _policy(audit_file=str(log)).evaluate(ASK)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[1])["prev"] == first["auditHash"] and verify_chain(lines) == 2
    small = _policy(audit_file=str(log), audit_max_bytes=4096)
    for _ in range(20):
        small.evaluate(ASK)
    assert log.with_name("a.jsonl.1").exists()
    assert verify_chain(log.read_text(encoding="utf-8").splitlines()) >= 1


@contextmanager
def _server(policy: AutonomyPolicy | None, token: str = "") -> Iterator[str]:
    server = CognitiveNodeServer(("127.0.0.1", 0), Path("."), Path("."), None, token, autonomy=policy)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _call(url: str, body: object | None = None, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})}
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode("utf-8"), method="GET" if body is None else "POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_the_routes_do_not_exist_while_it_is_off():
    with _server(None) as base:
        assert _call(base + "/autonomy/evaluate", ASK)[0] == 404
        assert _call(base + "/autonomy/policy")[0] == 404
        assert _call(base + "/autonomy/audit")[0] == 404


def test_the_routes_answer_when_it_is_on():
    with _server(_policy()) as base:
        status, answer = _call(base + "/autonomy/evaluate", dict(ASK, humanConfirmed=True))
        assert status == 200 and answer["decision"] == "allow"
        assert _call(base + "/autonomy/evaluate", dict(ASK, level="root"))[0] == 400
        assert _call(base + "/autonomy/policy")[1]["sources"]["vla-engine"] == "propose"
        entries = _call(base + "/autonomy/audit?limit=5")[1]["entries"]
        assert len(entries) == 1 and entries[0]["decision"] == "allow"
        assert _call(base + "/autonomy/audit?limit=0")[0] == 400


def test_the_token_is_needed_when_the_node_has_one():
    with _server(_policy(), token="t" * 20) as base:
        assert _call(base + "/autonomy/evaluate", ASK)[0] == 401
        assert _call(base + "/autonomy/policy")[0] == 401
        assert _call(base + "/autonomy/evaluate", ASK, token="t" * 20)[0] == 200


def test_no_decision_is_given_when_the_audit_cannot_be_written(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    with _server(_policy(audit_file=str(blocker / "sub" / "a.jsonl"))) as base:
        status, answer = _call(base + "/autonomy/evaluate", dict(ASK, humanConfirmed=True))
        assert status == 503 and "decision" not in answer
