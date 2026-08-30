# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_models.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

from pathlib import Path

from hydra_umc_cognitive_node.models import check_shared_models


def test_missing_models_directory_is_not_present(tmp_path: Path) -> None:
    status = check_shared_models(tmp_path)

    assert status.present is False
    assert status.path == tmp_path / "models"


def test_empty_models_directory_is_not_present(tmp_path: Path) -> None:
    (tmp_path / "models").mkdir()

    status = check_shared_models(tmp_path)

    assert status.present is False


def test_models_directory_with_real_content_is_present(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "vla-quantized.bin").write_bytes(b"not real weights, just real bytes")

    status = check_shared_models(tmp_path)

    assert status.present is True


def test_models_directory_with_only_a_subfolder_is_present(tmp_path: Path) -> None:
    # A real weights layout is a nested directory tree, not flat files -
    # `any(iterdir())` must not require a top-level file specifically.
    nested = tmp_path / "models" / "vla-engine"
    nested.mkdir(parents=True)
    (nested / "weights.hef").write_bytes(b"fixture")

    status = check_shared_models(tmp_path)

    assert status.present is True


def test_placeholder_and_configuration_files_do_not_claim_model_readiness(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    nested = models_dir / "vla-engine"
    nested.mkdir(parents=True)
    (models_dir / ".gitkeep").write_text("", encoding="utf-8")
    (nested / "README.md").write_text("weights are provisioned elsewhere", encoding="utf-8")
    (nested / "config.json").write_text("{}", encoding="utf-8")

    status = check_shared_models(tmp_path)

    assert status.present is False


def test_empty_candidate_artifact_does_not_claim_model_readiness(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "model.hef").write_bytes(b"")

    status = check_shared_models(tmp_path)

    assert status.present is False
