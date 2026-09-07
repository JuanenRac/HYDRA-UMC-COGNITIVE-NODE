# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_api.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real end-to-end HTTP tests: a real CognitiveNodeServer (ThreadingHTTPServer)
hit with real urllib requests - same convention as this family's other
test_api.py files. Reuses this repo's own tests/test_family.py fixture
shape for a real sibling-checkout workspace."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from hydra_umc_cognitive_node.api import CognitiveNodeServer
from hydra_umc_cognitive_node.family import EXPECTED_CHILDREN


def _write_manifest(workspace: Path, name: str, *, maturity: str = "scaffolding") -> None:
    repo = workspace / name
    repo.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0",
        "ecosystem": "HYDRA-UMC",
        "name": name,
        "version": "0.0.1",
        "role": "service",
        "maturity": maturity,
    }
    (repo / "hydra-umc.project.json").write_text(json.dumps(data), encoding="utf-8")


def _get(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


@contextmanager
def running_server(workspace: Path, repo_root: Path) -> Iterator[str]:
    server = CognitiveNodeServer(("127.0.0.1", 0), workspace, repo_root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_family_status_all_present(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    for child in EXPECTED_CHILDREN:
        _write_manifest(workspace, child, maturity="functional")
    with running_server(workspace, repo_root) as base:
        status, body = _get(f"{base}/family-status")
        assert status == 200
        assert body["all_children_present"] is True
        assert len(body["children"]) == len(EXPECTED_CHILDREN)
        assert body["shared_models"]["present"] is False  # repo_root/models/ doesn't exist


def test_family_status_reports_missing(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    with running_server(workspace, repo_root) as base:
        status, body = _get(f"{base}/family-status")
        assert status == 200
        assert body["all_children_present"] is False


def test_family_status_workspace_override(tmp_path: Path) -> None:
    default_workspace = tmp_path / "default"
    other_workspace = tmp_path / "other"
    other_workspace.mkdir()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    for child in EXPECTED_CHILDREN:
        _write_manifest(other_workspace, child, maturity="functional")
    with running_server(default_workspace, repo_root) as base:
        status, body = _get(f"{base}/family-status?workspace={other_workspace}")
        assert status == 200
        assert body["all_children_present"] is True


def test_shared_models_present_with_real_artifact(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repo_root = tmp_path / "repo"
    (repo_root / "models").mkdir(parents=True)
    (repo_root / "models" / "weights.gguf").write_bytes(b"fake weights")
    with running_server(workspace, repo_root) as base:
        status, body = _get(f"{base}/family-status")
        assert status == 200
        assert body["shared_models"]["present"] is True


def test_stats(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repo_root = tmp_path / "repo"
    with running_server(workspace, repo_root) as base:
        status, body = _get(f"{base}/stats")
        assert status == 200
        assert body["workspace"] == str(workspace)


def test_not_found(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repo_root = tmp_path / "repo"
    with running_server(workspace, repo_root) as base:
        status, body = _get(f"{base}/nope")
        assert status == 404
