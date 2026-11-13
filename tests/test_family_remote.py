# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_family_remote.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import json

import pytest

from hydra_umc_cognitive_node import main as cli
from hydra_umc_cognitive_node import remote
from hydra_umc_cognitive_node.family import EXPECTED_CHILDREN
from hydra_umc_cognitive_node.manifest import MAX_MANIFEST_BYTES, parse_child_manifest


def _manifest(name: str, version: str = "0.1.0") -> bytes:
    return json.dumps({"name": name, "version": version, "maturity": "alpha", "role": "service"}).encode()


def _fake(missing: set[str] | None = None, calls: list[str] | None = None):
    def fetch(url: str, timeout: float) -> bytes | None:
        if calls is not None:
            calls.append(url)
        child = url.split("/")[4]
        return None if missing and child in missing else _manifest(child)
    return fetch


def test_every_child_is_read_from_its_own_published_manifest() -> None:
    calls: list[str] = []
    statuses = remote.check_remote_family_status("v1.2.3", _fake(calls=calls))
    assert [s.name for s in statuses] == list(EXPECTED_CHILDREN)
    assert all(s.present and s.manifest is not None and s.manifest.version == "0.1.0" for s in statuses)
    assert calls == [f"https://raw.githubusercontent.com/JuanenRac/{c}/v1.2.3/hydra-umc.project.json" for c in EXPECTED_CHILDREN]


def test_a_child_that_cannot_be_read_is_not_found_not_an_error() -> None:
    statuses = remote.check_remote_family_status("main", _fake(missing={"HYDRA-UMC-VOICE-UI"}))
    by_name = {s.name: s for s in statuses}
    assert by_name["HYDRA-UMC-VOICE-UI"].present is False
    assert by_name["HYDRA-UMC-VLA-ENGINE"].present is True


def test_an_answer_that_is_not_a_manifest_is_not_found() -> None:
    for body in (b"not json", b"[1, 2]", b"\xff\xfe", json.dumps({"name": "x"}).encode()):
        statuses = remote.check_remote_family_status("main", lambda url, timeout, body=body: body)
        assert not any(s.present for s in statuses)


@pytest.mark.parametrize("ref", ["", "../x", "a/b", "a..b", "-x", "x y", "main?x=1", "a" * 65, "a\nb"])
def test_a_ref_that_is_not_a_plain_name_is_refused(ref: str) -> None:
    with pytest.raises(ValueError):
        remote.manifest_url("HYDRA-UMC-VLA-ENGINE", ref)


def test_a_child_that_is_not_expected_is_refused() -> None:
    with pytest.raises(ValueError):
        remote.manifest_url("SOMEONE-ELSE", "main")


def test_the_real_fetcher_asks_only_for_the_published_host() -> None:
    assert remote.fetch_https("http://raw.githubusercontent.com/JuanenRac/x/main/a", 1.0) is None
    assert remote.fetch_https("https://example.com/hydra-umc.project.json", 1.0) is None
    assert remote.fetch_https("file:///etc/passwd", 1.0) is None


def test_the_real_fetcher_degrades_on_a_network_error_and_an_oversized_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    class Answer:
        def __init__(self, size: int) -> None:
            self.size = size

        def __enter__(self):
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self, limit: int) -> bytes:
            return b"x" * min(self.size, limit)

    class Opener:
        def __init__(self, result: object) -> None:
            self.result = result

        def open(self, request: object, timeout: float = 0.0):
            if isinstance(self.result, Exception):
                raise self.result
            return self.result

    url = remote.manifest_url("HYDRA-UMC-VLA-ENGINE")
    monkeypatch.setattr(remote.urllib.request, "build_opener", lambda *a: Opener(OSError("down")))
    assert remote.fetch_https(url, 1.0) is None
    monkeypatch.setattr(remote.urllib.request, "build_opener", lambda *a: Opener(Answer(MAX_MANIFEST_BYTES + 10)))
    assert remote.fetch_https(url, 1.0) is None
    monkeypatch.setattr(remote.urllib.request, "build_opener", lambda *a: Opener(Answer(10)))
    assert remote.fetch_https(url, 1.0) == b"x" * 10


def test_parse_child_manifest_matches_what_the_local_reader_accepts() -> None:
    assert parse_child_manifest(_manifest("A").decode()) is not None
    assert parse_child_manifest("") is None
    assert parse_child_manifest(json.dumps({"name": " ", "version": "1", "maturity": "m", "role": "r"})) is None


def test_the_command_reads_the_published_manifests_only_when_asked(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path) -> None:
    seen: list[str] = []
    monkeypatch.setattr(cli, "check_remote_family_status", lambda ref: remote.check_remote_family_status(ref, _fake(calls=seen)))
    code = cli.main(["family-status", "--workspace", str(tmp_path), "--models-dir", str(tmp_path), "--json", "--remote", "--remote-ref", "v9"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["all_children_present"] is True and len(seen) == 4 and "/v9/" in seen[0]
    seen.clear()
    code = cli.main(["family-status", "--workspace", str(tmp_path), "--models-dir", str(tmp_path), "--json"])
    assert code == 1 and seen == []


def test_remote_and_probe_cannot_be_mixed_and_a_bad_ref_stops_with_2(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["family-status", "--workspace", str(tmp_path), "--remote", "--probe"]) == 2
    assert cli.main(["family-status", "--workspace", str(tmp_path), "--remote", "--remote-ref", "../x"]) == 2
    assert "error:" in capsys.readouterr().err
