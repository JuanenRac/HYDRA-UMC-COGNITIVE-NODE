# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_family.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

from hydra_umc_cognitive_node.family import (
    EXPECTED_CHILDREN,
    MINIMUMS_ENVIRONMENT,
    is_compatible,
    load_minimum_versions,
    parse_version,
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


def test_versions_are_read_with_three_or_four_components_and_nothing_else() -> None:
    assert parse_version("0.8.1") == (0, 8, 1, 0)
    assert parse_version(" 0.8.1.2 ") == (0, 8, 1, 2)
    for bad in ("", "1", "1.2.3.4.5", "v1.2.3", "1.2.3-rc1", "a.b.c", None, 3):
        assert parse_version(bad) is None  # type: ignore[arg-type]


def test_a_version_is_compared_as_numbers_not_as_text() -> None:
    assert is_compatible("0.10.0", "0.9.0") is True
    assert is_compatible("0.9.0", "0.9.0") is True
    assert is_compatible("0.9.0", "0.9.0.1") is False
    assert is_compatible("0.9.0", "garbage") is None
    assert is_compatible("garbage", "0.9.0") is None


def test_the_minimums_come_from_the_file_the_variable_names_and_a_bad_file_gives_none(tmp_path: Path) -> None:
    good = tmp_path / "minimums.json"
    good.write_text(json.dumps({"HYDRA-UMC-VOICE-UI": "0.2.0", "HYDRA-UMC-DOCS-QA": "oops", "extra": "1.0.0"}), encoding="utf-8")
    assert load_minimum_versions(env={MINIMUMS_ENVIRONMENT: str(good)}) == {"HYDRA-UMC-VOICE-UI": "0.2.0", "extra": "1.0.0"}
    assert load_minimum_versions(env={}) == {}
    assert load_minimum_versions(env={MINIMUMS_ENVIRONMENT: str(tmp_path / "missing.json")}) == {}
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert load_minimum_versions(str(broken)) == {}
    listed = tmp_path / "list.json"
    listed.write_text("[1, 2]", encoding="utf-8")
    assert load_minimum_versions(str(listed)) == {}
    huge = tmp_path / "huge.json"
    huge.write_text(" " * (64 * 1024 + 1), encoding="utf-8")
    assert load_minimum_versions(str(huge)) == {}


def test_a_child_older_than_its_minimum_is_reported_and_the_whole_family_is_not_compatible(tmp_path: Path) -> None:
    for child in EXPECTED_CHILDREN:
        _write_manifest(tmp_path, child, maturity="functional")  # every child is 0.0.1
    statuses = check_family_status(tmp_path)
    shared_models = SharedModelsStatus(present=True, path=tmp_path / "models")

    result = family_status_to_dict(statuses, shared_models, minimums={"HYDRA-UMC-VOICE-UI": "0.2.0", "HYDRA-UMC-DOCS-QA": "0.0.1"})

    by_name = {c["name"]: c for c in result["children"]}
    assert by_name["HYDRA-UMC-VOICE-UI"]["compatible"] is False and by_name["HYDRA-UMC-VOICE-UI"]["minimum_version"] == "0.2.0"
    assert by_name["HYDRA-UMC-DOCS-QA"]["compatible"] is True
    assert by_name["HYDRA-UMC-VLA-ENGINE"]["compatible"] is None and by_name["HYDRA-UMC-VLA-ENGINE"]["minimum_version"] is None
    assert result["all_children_compatible"] is False


def test_with_no_minimums_the_answer_has_none_of_the_compatibility_fields(tmp_path: Path) -> None:
    for child in EXPECTED_CHILDREN:
        _write_manifest(tmp_path, child)
    result = family_status_to_dict(check_family_status(tmp_path), SharedModelsStatus(present=True, path=tmp_path / "models"), minimums={})
    assert "all_children_compatible" not in result
    assert all("compatible" not in child and "minimum_version" not in child for child in result["children"])


def test_a_missing_child_with_a_minimum_says_nothing_about_compatibility(tmp_path: Path) -> None:
    result = family_status_to_dict(check_family_status(tmp_path), SharedModelsStatus(present=False, path=tmp_path), minimums={"HYDRA-UMC-VOICE-UI": "1.0.0"})
    voice = next(c for c in result["children"] if c["name"] == "HYDRA-UMC-VOICE-UI")
    assert voice["compatible"] is None and result["all_children_compatible"] is True
