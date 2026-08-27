# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydra_umc_cognitive_node.main import main


def _write_manifest(workspace: Path, name: str) -> None:
    repo = workspace / name
    repo.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0", "ecosystem": "HYDRA-UMC", "name": name,
        "version": "0.0.2", "role": "service", "maturity": "functional",
    }
    (repo / "hydra-umc.project.json").write_text(json.dumps(data), encoding="utf-8")


def test_bare_invocation_prints_identity(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "HYDRA-UMC-COGNITIVE-NODE v" in captured.out


def test_family_status_all_present(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for child in ("HYDRA-UMC-VLA-ENGINE", "HYDRA-UMC-VOICE-UI", "HYDRA-UMC-SEMANTIC-PLANNER", "HYDRA-UMC-DOCS-QA"):
        _write_manifest(tmp_path, child)

    exit_code = main(["family-status", "--workspace", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "All 4 children present" in captured.out
    assert "maturity=functional" in captured.out


def test_family_status_missing_children(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["family-status", "--workspace", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "NOT FOUND" in captured.out
    assert "4 of 4 children not found" in captured.out
