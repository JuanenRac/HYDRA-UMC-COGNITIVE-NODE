# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/models.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Real check of this node's own shared model-weights directory.

`docker-compose.yml`'s own header comment says this repo "owns the
HydraOS image (os/) and the quantized LLM/VLA weights (models/) shared
by its four children", and mounts `./models` read-only into the
container. The directory is kept in the repository (with a placeholder
file) but holds no weights until they are provisioned onto the machine,
which is itself honest information a family-readiness
check should surface rather than silently ignore: a caller deciding
whether this node's family is actually ready to run needs to know the
shared weights the children depend on are missing, not just that the
sibling repositories are checked out.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .model_weights import ANY_WEIGHT_SUFFIXES, contains_model_artifact

MODELS_DIR_NAME = "models"

# Upper bound on the files one readiness probe looks at.
MAX_FILES_INSPECTED = 20_000

# A checked-out `models/` tree can legitimately contain documentation,
# empty directories, `.gitkeep`, tokenizers, and configuration files before
# any runnable Hailo/LLM weight is provisioned. Those must not turn the
# family's model-readiness signal green. This is intentionally an inventory
# check, not a claim that the artifact is compatible with the real Hailo-10
# runtime (that requires the physical runtime and model validation).
MODEL_ARTIFACT_SUFFIXES: Final[frozenset[str]] = ANY_WEIGHT_SUFFIXES


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


def check_shared_models(repo_root: Path, models_dir: Path | None = None) -> SharedModelsStatus:
    """Real check of this node's own shared weights directory, not a
    sibling's: `models_dir` when given (a container mounts the weights
    somewhere other than next to the installed package), otherwise
    `repo_root/models/`. `repo_root` is this repository's own root (see
    `main.py`'s `_REPO_ROOT`), never the workspace root `family-status
    --workspace` scans for sibling checkouts."""
    if models_dir is None:
        models_dir = repo_root / MODELS_DIR_NAME
    present = _contains_candidate_model_artifact(models_dir)
    return SharedModelsStatus(present=present, path=models_dir)


def _contains_candidate_model_artifact(models_dir: Path) -> bool:
    """Return whether ``models_dir`` contains a non-empty local candidate.

    The walk is the one the family shares (``model_weights.py``, vendored byte for byte from the shared SDK): it does not follow
    symlinked directories or accept symlinked files, so a readiness probe of this repository cannot escape its own models tree,
    it stops after ``MAX_FILES_INSPECTED`` files, and any filesystem error degrades to ``False`` rather than making
    ``family-status`` crash.
    """
    return contains_model_artifact(models_dir, MODEL_ARTIFACT_SUFFIXES, MAX_FILES_INSPECTED)
