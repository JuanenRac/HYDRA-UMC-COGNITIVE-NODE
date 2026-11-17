# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_autonomy_source_credential.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A source of the autonomy policy can have a credential of its own."""
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
    LANGUAGES,
    REASONS,
    AutonomyConfigError,
    AutonomyPolicy,
    parse_autonomy_config,
)

SOURCE_TOKEN = "s" * 24
NODE_TOKEN = "n" * 24
ASK = {"source": "vla-engine", "kind": "proposal", "actionId": "move-1", "level": "propose"}


def _policy(tmp_path: Path, **extra: object) -> AutonomyPolicy:
    token = tmp_path / "vla.token"
    token.write_text(SOURCE_TOKEN + "\n", encoding="utf-8")
    raw = {"enabled": True, "sources": {"vla-engine": {"level": "propose", "tokenFile": str(token)}, "voice-ui": "execute_with_confirmation"}, **extra}
    return AutonomyPolicy(parse_autonomy_config(raw))


def test_the_right_token_gets_the_level_of_the_source(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    answer = policy.evaluate(ASK, SOURCE_TOKEN)
    assert answer["decision"] == "allow" and answer["reason"] == "allowed" and answer["grantedLevel"] == "propose"
    assert policy.audit.recent(1)[0]["credential"] == "proven"


@pytest.mark.parametrize("presented", ["", NODE_TOKEN, SOURCE_TOKEN + "x", SOURCE_TOKEN[:-1]])
def test_any_other_token_cannot_use_the_name_of_the_source(tmp_path: Path, presented: str) -> None:
    policy = _policy(tmp_path)
    for level in ("inform", "propose"):
        answer = policy.evaluate({**ASK, "level": level}, presented)
        assert answer["decision"] == "deny" and answer["reason"] == "source_credential"
    assert policy.audit.recent(1)[0]["credential"] == "required"


def test_a_source_without_credential_behaves_as_before(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    answer = policy.evaluate({"source": "voice-ui", "kind": "intent", "actionId": "a1", "level": "execute_with_confirmation"}, NODE_TOKEN)
    assert answer["decision"] == "needs_confirmation"
    assert "credential" not in policy.audit.recent(1)[0]
    assert policy.evaluate({"source": "voice-ui", "kind": "intent", "actionId": "a1", "level": "inform"})["decision"] == "allow"


def test_the_old_form_of_the_policy_is_still_read() -> None:
    config = parse_autonomy_config({"enabled": True, "sources": {"vla-engine": "propose"}})
    assert config.sources == {"vla-engine": "propose"} and config.source_token_files == {}
    assert "sourcesWithCredential" not in AutonomyPolicy(config).describe()


def test_the_policy_lists_the_names_with_a_credential_and_nothing_more(tmp_path: Path) -> None:
    shown = _policy(tmp_path).describe()
    assert shown["sourcesWithCredential"] == ["vla-engine"] and shown["sources"]["vla-engine"] == "propose"
    assert SOURCE_TOKEN not in str(shown) and "vla.token" not in str(shown)


def test_a_credential_that_cannot_be_used_stops_the_policy(tmp_path: Path) -> None:
    with pytest.raises(AutonomyConfigError, match="cannot read"):
        AutonomyPolicy(parse_autonomy_config({"enabled": True, "sources": {"a": {"level": "inform", "tokenFile": str(tmp_path / "missing")}}}))
    short = tmp_path / "short"
    short.write_text("abc", encoding="utf-8")
    with pytest.raises(AutonomyConfigError, match="at least 16"):
        AutonomyPolicy(parse_autonomy_config({"enabled": True, "sources": {"a": {"level": "inform", "tokenFile": str(short)}}}))


@pytest.mark.parametrize("bad", [
    {"a": {"level": "root"}}, {"a": {"level": "inform", "extra": 1}}, {"a": {"level": "inform", "tokenFile": ""}}, {"a": {"level": "inform", "tokenFile": 3}}, {"a": {}},
])
def test_a_badly_written_source_is_refused(bad: dict) -> None:
    with pytest.raises(AutonomyConfigError):
        parse_autonomy_config({"enabled": True, "sources": bad})


def test_the_reason_exists_in_the_eight_languages() -> None:
    assert set(REASONS["source_credential"]) == set(LANGUAGES)
    assert all(REASONS["source_credential"][language] for language in LANGUAGES)


@contextmanager
def _server(policy: AutonomyPolicy, token: str = "") -> Iterator[str]:
    server = CognitiveNodeServer(("127.0.0.1", 0), Path("."), Path("."), None, token, autonomy=policy)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _call(url: str, body: object, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})}
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_over_http_the_token_presented_decides_the_source(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    with _server(policy, token=NODE_TOKEN) as base:
        assert _call(base + "/autonomy/evaluate", ASK, token=NODE_TOKEN)[1]["reason"] == "source_credential"    # the token of the node is not the one of the source
        assert _call(base + "/autonomy/evaluate", ASK)[0] == 401
    with _server(_policy(tmp_path)) as base:
        assert _call(base + "/autonomy/evaluate", ASK, token=SOURCE_TOKEN)[1]["decision"] == "allow"
