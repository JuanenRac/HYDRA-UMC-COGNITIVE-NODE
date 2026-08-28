# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_family.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

from hydra_umc_cognitive_node.family import (
    EXPECTED_CHILDREN,
    FAMILY_STATUS_SCHEMA_VERSION,
    check_family_status,
    family_status_to_dict,
)
from hydra_umc_cognitive_node.models import SharedModelsStatus


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


def test_expected_children_matches_the_real_readme_family() -> None:
    assert set(EXPECTED_CHILDREN) == {
        "HYDRA-UMC-VLA-ENGINE",
        "HYDRA-UMC-VOICE-UI",
        "HYDRA-UMC-SEMANTIC-PLANNER",
        "HYDRA-UMC-DOCS-QA",
    }


def test_all_children_present(tmp_path: Path) -> None:
    for child in EXPECTED_CHILDREN:
        _write_manifest(tmp_path, child, maturity="functional")

    statuses = check_family_status(tmp_path)

    assert len(statuses) == len(EXPECTED_CHILDREN)
    assert all(status.present for status in statuses)
    assert all(status.manifest is not None and status.manifest.maturity == "functional" for status in statuses)


def test_some_children_missing(tmp_path: Path) -> None:
    _write_manifest(tmp_path, "HYDRA-UMC-VOICE-UI")
    _write_manifest(tmp_path, "HYDRA-UMC-DOCS-QA")

    statuses = check_family_status(tmp_path)

    present = {status.name for status in statuses if status.present}
    missing = {status.name for status in statuses if not status.present}
    assert present == {"HYDRA-UMC-VOICE-UI", "HYDRA-UMC-DOCS-QA"}
    assert missing == {"HYDRA-UMC-VLA-ENGINE", "HYDRA-UMC-SEMANTIC-PLANNER"}


def test_empty_workspace_reports_all_missing(tmp_path: Path) -> None:
    statuses = check_family_status(tmp_path)

    assert all(not status.present for status in statuses)


def test_family_status_to_dict_real_schema_shape(tmp_path: Path) -> None:
    _write_manifest(tmp_path, "HYDRA-UMC-VOICE-UI", maturity="functional")
    statuses = check_family_status(tmp_path)
    shared_models = SharedModelsStatus(present=False, path=tmp_path / "models")

    result = family_status_to_dict(statuses, shared_models)

    assert result["schema_version"] == FAMILY_STATUS_SCHEMA_VERSION
    assert result["shared_models"] == {"present": False, "path": str(tmp_path / "models")}
    assert result["all_children_present"] is False
    voice_ui = next(c for c in result["children"] if c["name"] == "HYDRA-UMC-VOICE-UI")
    assert voice_ui == {
        "name": "HYDRA-UMC-VOICE-UI",
        "present": True,
        "version": "0.0.1",
        "maturity": "functional",
        "role": "service",
    }
    missing_child = next(c for c in result["children"] if c["name"] == "HYDRA-UMC-VLA-ENGINE")
    assert missing_child == {
        "name": "HYDRA-UMC-VLA-ENGINE",
        "present": False,
        "version": None,
        "maturity": None,
        "role": None,
    }


def test_family_status_to_dict_all_present_is_true_when_real(tmp_path: Path) -> None:
    for child in EXPECTED_CHILDREN:
        _write_manifest(tmp_path, child, maturity="functional")
    statuses = check_family_status(tmp_path)
    shared_models = SharedModelsStatus(present=True, path=tmp_path / "models")

    result = family_status_to_dict(statuses, shared_models)

    assert result["all_children_present"] is True
    assert result["shared_models"]["present"] is True
