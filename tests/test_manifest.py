# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_manifest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

from hydra_umc_cognitive_node.manifest import MAX_MANIFEST_BYTES, read_child_manifest


def _write_manifest(repo_path: Path, **fields: str) -> None:
    repo_path.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0",
        "ecosystem": "HYDRA-UMC",
        "name": "HYDRA-UMC-EXAMPLE",
        "version": "0.0.1",
        "role": "service",
        "maturity": "scaffolding",
        **fields,
    }
    (repo_path / "hydra-umc.project.json").write_text(json.dumps(data), encoding="utf-8")


def test_reads_a_real_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "HYDRA-UMC-EXAMPLE"
    _write_manifest(repo, version="0.0.5", maturity="functional", role="tool")

    manifest = read_child_manifest(repo)

    assert manifest is not None
    assert manifest.name == "HYDRA-UMC-EXAMPLE"
    assert manifest.version == "0.0.5"
    assert manifest.maturity == "functional"
    assert manifest.role == "tool"


def test_missing_repository_returns_none(tmp_path: Path) -> None:
    assert read_child_manifest(tmp_path / "does-not-exist") is None


def test_missing_manifest_file_returns_none(tmp_path: Path) -> None:
    repo = tmp_path / "empty-repo"
    repo.mkdir()

    assert read_child_manifest(repo) is None


def test_malformed_json_returns_none_not_a_crash(tmp_path: Path) -> None:
    repo = tmp_path / "broken-repo"
    repo.mkdir()
    (repo / "hydra-umc.project.json").write_text("{not valid json", encoding="utf-8")

    assert read_child_manifest(repo) is None


def test_missing_required_field_returns_none(tmp_path: Path) -> None:
    repo = tmp_path / "incomplete-repo"
    repo.mkdir()
    (repo / "hydra-umc.project.json").write_text(json.dumps({"name": "X"}), encoding="utf-8")

    assert read_child_manifest(repo) is None


def test_oversized_manifest_returns_none_without_reading_it(tmp_path: Path) -> None:
    # A real resource-limit guard: a manifest bigger than any real one in
    # this ecosystem ever legitimately is (a corrupted or malicious
    # checkout) must degrade the same as any other malformed manifest,
    # never be fully read into memory.
    repo = tmp_path / "oversized-repo"
    repo.mkdir()
    padding = " " * (MAX_MANIFEST_BYTES + 1)
    oversized = json.dumps({"padding": padding, "name": "X", "version": "0.0.1", "role": "service", "maturity": "functional"})
    assert len(oversized.encode("utf-8")) > MAX_MANIFEST_BYTES
    (repo / "hydra-umc.project.json").write_text(oversized, encoding="utf-8")

    assert read_child_manifest(repo) is None


def test_manifest_right_at_the_limit_is_still_read(tmp_path: Path) -> None:
    repo = tmp_path / "at-limit-repo"
    repo.mkdir()
    data = {"name": "X", "version": "0.0.1", "role": "service", "maturity": "functional"}
    encoded = json.dumps(data).encode("utf-8")
    assert len(encoded) <= MAX_MANIFEST_BYTES
    (repo / "hydra-umc.project.json").write_bytes(encoded)

    manifest = read_child_manifest(repo)

    assert manifest is not None
    assert manifest.name == "X"
