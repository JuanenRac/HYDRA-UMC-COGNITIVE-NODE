# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_probe.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Asking the running children for their health, the image tags and the compose file."""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from hydra_umc_cognitive_node import main as node_main
from hydra_umc_cognitive_node.api import CognitiveNodeServer
from hydra_umc_cognitive_node.family import EXPECTED_CHILDREN, check_family_status, env_versions
from hydra_umc_cognitive_node.probe import (
    CHILD_URLS_ENV,
    DEFAULT_CHILD_PORTS,
    child_base_urls,
    health_path_of,
    probe_child,
    probe_family,
)

ROOT = Path(__file__).resolve().parent.parent


class Child:
    """A stand-in for one child service: answers a fixed status and body on one path."""

    def __init__(self, status: int = 200, body: object = None, path: str = "/stats") -> None:
        answer = json.dumps(body if body is not None else {"status": "ok"}).encode()
        wanted = path

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path != wanted:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(answer)))
                self.end_headers()
                self.wfile.write(answer)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def _manifest(workspace: Path, name: str, version: str = "0.3.1", health_path: str | None = None) -> None:
    repo = workspace / name
    repo.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": "1.0", "ecosystem": "HYDRA-UMC", "name": name, "version": version, "role": "service", "maturity": "functional"}
    if health_path is not None:
        data["service"] = {"health_path": health_path}
    (repo / "hydra-umc.project.json").write_text(json.dumps(data), encoding="utf-8")


def test_the_default_addresses_are_the_loopback_ports_of_the_units() -> None:
    urls = child_base_urls({})
    assert set(urls) == set(EXPECTED_CHILDREN)
    assert urls["HYDRA-UMC-VLA-ENGINE"] == "http://127.0.0.1:8098"
    assert {n: int(u.rsplit(":", 1)[1]) for n, u in urls.items()} == DEFAULT_CHILD_PORTS


def test_the_addresses_can_be_replaced_for_a_container() -> None:
    urls = child_base_urls({CHILD_URLS_ENV: "HYDRA-UMC-VOICE-UI=http://voice-ui:8091/, HYDRA-UMC-DOCS-QA=https://docs:9/"})
    assert urls["HYDRA-UMC-VOICE-UI"] == "http://voice-ui:8091"
    assert urls["HYDRA-UMC-DOCS-QA"] == "https://docs:9"
    assert urls["HYDRA-UMC-VLA-ENGINE"] == "http://127.0.0.1:8098"


@pytest.mark.parametrize(
    "bad",
    [
        "HYDRA-UMC-VOICE-UI",
        "NOT-A-CHILD=http://x:1",
        "HYDRA-UMC-VOICE-UI=ftp://x:1",
        "HYDRA-UMC-VOICE-UI=file:///etc/passwd",
        "HYDRA-UMC-VOICE-UI=http://user:pw@x:1",
        "HYDRA-UMC-VOICE-UI=//x:1",
    ],
)
def test_an_address_that_is_not_an_http_service_of_a_child_is_refused(bad: str) -> None:
    with pytest.raises(ValueError):
        child_base_urls({CHILD_URLS_ENV: bad})


def test_the_health_route_comes_from_the_manifest_of_the_child(tmp_path: Path) -> None:
    _manifest(tmp_path, "HYDRA-UMC-VOICE-UI", health_path="/health")
    _manifest(tmp_path, "HYDRA-UMC-DOCS-QA")
    assert health_path_of(tmp_path, "HYDRA-UMC-VOICE-UI") == "/health"
    assert health_path_of(tmp_path, "HYDRA-UMC-DOCS-QA") == "/stats"
    assert health_path_of(tmp_path, "HYDRA-UMC-VLA-ENGINE") == "/stats", "a child that is not checked out"
    _manifest(tmp_path, "HYDRA-UMC-SEMANTIC-PLANNER", health_path="not-a-path")
    assert health_path_of(tmp_path, "HYDRA-UMC-SEMANTIC-PLANNER") == "/stats"


def test_a_child_that_answers_well_is_healthy_and_a_verdict_in_the_answer_is_believed() -> None:
    child = Child(body={"status": "ok"})
    try:
        result = probe_child("HYDRA-UMC-DOCS-QA", child.url, "/stats")
        assert (result.reachable, result.http_status, result.healthy, result.error) == (True, 200, True, None)
        assert result.latency_ms is not None
    finally:
        child.close()
    sick = Child(body={"healthy": False, "state": "stalled"})
    try:
        assert probe_child("x", sick.url, "/stats").healthy is False
    finally:
        sick.close()
    plain = Child(body=[1, 2, 3])
    try:
        assert probe_child("x", plain.url, "/stats").healthy is True, "a 2xx answer with no verdict of its own is up"
    finally:
        plain.close()


def test_a_child_that_answers_with_an_error_status_is_reachable_but_not_healthy() -> None:
    child = Child(status=503, body={"healthy": False})
    try:
        result = probe_child("x", child.url, "/stats")
        assert (result.reachable, result.http_status, result.healthy) == (True, 503, False)
    finally:
        child.close()


def test_a_child_that_does_not_answer_is_not_reachable_and_the_reason_is_kept() -> None:
    result = probe_child("x", "http://127.0.0.1:1", "/stats", timeout=1.0)
    assert (result.reachable, result.http_status, result.healthy) == (False, None, None)
    assert result.error


def test_the_whole_family_is_probed_with_the_health_route_of_each(tmp_path: Path) -> None:
    voice = Child(path="/health")
    planner = Child(path="/stats", body={"healthy": False})
    try:
        _manifest(tmp_path, "HYDRA-UMC-VOICE-UI", health_path="/health")
        env = {CHILD_URLS_ENV: f"HYDRA-UMC-VOICE-UI={voice.url},HYDRA-UMC-SEMANTIC-PLANNER={planner.url}"}
        by_name = {h.name: h for h in probe_family(tmp_path, env)}
        assert by_name["HYDRA-UMC-VOICE-UI"].healthy is True
        assert by_name["HYDRA-UMC-SEMANTIC-PLANNER"].healthy is False
        assert by_name["HYDRA-UMC-DOCS-QA"].reachable is False
    finally:
        voice.close()
        planner.close()


def test_the_cli_probe_fails_when_a_child_is_not_answering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for name in EXPECTED_CHILDREN:
        _manifest(tmp_path, name)
    live = Child()
    try:
        monkeypatch.setenv(CHILD_URLS_ENV, ",".join(f"{n}={live.url}" for n in EXPECTED_CHILDREN[:3]))
        code = node_main.main(["family-status", "--workspace", str(tmp_path), "--probe", "--json"])
        report = json.loads(capsys.readouterr().out)
        assert code == 1
        assert report["all_children_present"] is True and report["all_children_healthy"] is False
        health = {c["name"]: c["health"] for c in report["children"]}
        assert health[EXPECTED_CHILDREN[0]]["healthy"] is True
        assert health[EXPECTED_CHILDREN[3]]["reachable"] is False
        monkeypatch.setenv(CHILD_URLS_ENV, ",".join(f"{n}={live.url}" for n in EXPECTED_CHILDREN))
        assert node_main.main(["family-status", "--workspace", str(tmp_path), "--probe"]) == 0
        assert "healthy" in capsys.readouterr().out
    finally:
        live.close()


def test_without_probe_the_report_is_what_it_was(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for name in EXPECTED_CHILDREN:
        _manifest(tmp_path, name)
    assert node_main.main(["family-status", "--workspace", str(tmp_path), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert "all_children_healthy" not in report and all("health" not in c for c in report["children"])


def test_a_bad_address_list_stops_the_probe_with_a_clear_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv(CHILD_URLS_ENV, "nonsense")
    assert node_main.main(["family-status", "--workspace", str(tmp_path), "--probe"]) == 2
    assert CHILD_URLS_ENV in capsys.readouterr().err


def test_the_api_asks_the_children_only_when_told_to(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    for name in EXPECTED_CHILDREN:
        _manifest(tmp_path, name)
    live = Child()
    monkeypatch.setenv(CHILD_URLS_ENV, ",".join(f"{n}={live.url}" for n in EXPECTED_CHILDREN))
    server = CognitiveNodeServer(("127.0.0.1", 0), tmp_path, ROOT)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        plain = json.loads(urllib.request.urlopen(f"{base}/family-status", timeout=5).read())
        assert "all_children_healthy" not in plain
        probed = json.loads(urllib.request.urlopen(f"{base}/family-status?probe=1", timeout=5).read())
        assert probed["all_children_healthy"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        live.close()


def test_versions_for_the_env_file_come_from_the_manifests(tmp_path: Path) -> None:
    _manifest(tmp_path, "HYDRA-UMC-VLA-ENGINE", version="0.1.7")
    _manifest(tmp_path, "HYDRA-UMC-DOCS-QA", version="0.2.0")
    lines = env_versions(check_family_status(tmp_path))
    assert lines == ["HYDRA_UMC_VLA_ENGINE_VERSION=0.1.7", "HYDRA_UMC_DOCS_QA_VERSION=0.2.0"]


# ---- the compose file ----


def _compose() -> str:
    return (ROOT / "docker-compose.yml").read_text(encoding="utf-8")


def _service(name: str) -> str:
    text = _compose()
    match = re.search(rf"^  {re.escape(name)}:\n(.*?)(?=^  [a-z][a-z-]*:\n|\Z)", text.replace("\r\n", "\n"), re.S | re.M)
    assert match, name
    return match.group(1)


def test_the_vla_engine_sees_the_shared_weights_where_it_looks_for_them() -> None:
    # the engine looks in <workspace>/HYDRA-UMC-COGNITIVE-NODE/models; its image sets the workspace to /workspace
    assert "./models:/workspace/HYDRA-UMC-COGNITIVE-NODE/models:ro" in _service("vla-engine")


def test_the_images_are_tagged_with_a_version_that_is_not_made_up() -> None:
    text = _compose()
    assert "1.0.0" not in re.sub(r"#.*", "", text), "no image carries an invented 1.0.0 any more"
    for service, variable in (
        ("cognitive-node", "HYDRA_UMC_COGNITIVE_NODE_VERSION"),
        ("voice-ui", "HYDRA_UMC_VOICE_UI_VERSION"),
        ("semantic-planner", "HYDRA_UMC_SEMANTIC_PLANNER_VERSION"),
        ("vla-engine", "HYDRA_UMC_VLA_ENGINE_VERSION"),
        ("docs-qa", "HYDRA_UMC_DOCS_QA_VERSION"),
    ):
        assert f":${{{variable}:-latest}}" in _service(service), service


def test_the_node_is_told_where_its_children_are_inside_the_stack() -> None:
    node = _service("cognitive-node")
    assert CHILD_URLS_ENV in node
    for child, port in (("voice-ui", 8091), ("semantic-planner", 8109), ("vla-engine", 8098), ("docs-qa", 8110)):
        assert f"http://{child}:{port}" in node
