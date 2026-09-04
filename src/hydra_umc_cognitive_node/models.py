# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/models.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real check of this node's own shared model-weights directory.

`docker-compose.yml`'s own header comment says this repo "owns the
HydraOS image (os/) and the quantized LLM/VLA weights (models/) shared
by its four children", and mounts `./models` read-only into the
container. `models/` is real and already exists in this checkout - it is
just empty today (no weights have been provisioned onto this dev
machine), which is itself real, honest information a family-readiness
check should surface rather than silently ignore: a caller deciding
whether this node's family is actually ready to run needs to know the
shared weights the children depend on are missing, not just that the
sibling repositories are checked out.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

MODELS_DIR_NAME = "models"

# A checked-out `models/` tree can legitimately contain documentation,
# empty directories, `.gitkeep`, tokenizers, and configuration files before
# any runnable Hailo/LLM weight is provisioned. Those must not turn the
# family's model-readiness signal green. This is intentionally an inventory
# check, not a claim that the artifact is compatible with the real Hailo-10
# runtime (that requires the physical runtime and model validation).
MODEL_ARTIFACT_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".bin", ".gguf", ".har", ".hef", ".onnx", ".safetensors", ".tflite"}
)


@dataclass(frozen=True)
class SharedModelsStatus:
    """Whether this node's own real `models/` directory has real content.

    `present` is deliberately about a non-empty candidate weight artifact,
    not just the directory existing. Empty directories, `.gitkeep`, generic
    documentation, and tokenizer/config-only trees therefore remain
    honestly reported as unavailable. It does not claim a candidate artifact
    is compatible with a physical Hailo-10 runtime.
    """

    present: bool
    path: Path


def check_shared_models(repo_root: Path) -> SharedModelsStatus:
    """Real check of `repo_root/models/` - this node's own shared weights
    directory, not a sibling's. `repo_root` is this repository's own
    root (see `main.py`'s `_REPO_ROOT`), never the workspace root
    `family-status --workspace` scans for sibling checkouts."""
    models_dir = repo_root / MODELS_DIR_NAME
    present = _contains_candidate_model_artifact(models_dir)
    return SharedModelsStatus(present=present, path=models_dir)


def _contains_candidate_model_artifact(models_dir: Path) -> bool:
    """Return whether ``models_dir`` contains a non-empty local candidate.

    Traversal does not follow symlinked directories or accept symlinked files:
    a readiness probe of this repository must not escape its own models tree.
    Any filesystem error degrades to ``False`` rather than making
    ``family-status`` crash.
    """
    if not models_dir.is_dir() or models_dir.is_symlink():
        return False

    try:
        # os.walk(..., followlinks=False) - not Path.rglob("*") - is the
        # real, version-independent way to keep this walk inside the
        # models/ tree. pathlib's own recursive "**" traversal only grew a
        # way to refuse symlinked directories in Python 3.13's
        # recurse_symlinks parameter; on every earlier 3.x release this
        # project actually declares support for (requires-python >=3.10),
        # Path.rglob("*") has no such option and always follows a
        # symlinked subdirectory, silently defeating this exact guarantee.
        for root, dirnames, filenames in os.walk(models_dir, followlinks=False):
            for filename in filenames:
                path = Path(root, filename)
                if path.is_symlink() or not path.is_file():
                    continue
                if path.suffix.lower() in MODEL_ARTIFACT_SUFFIXES and path.stat().st_size > 0:
                    return True
    except OSError:
        return False
    return False
