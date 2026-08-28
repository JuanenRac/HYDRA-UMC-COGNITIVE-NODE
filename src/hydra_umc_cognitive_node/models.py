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

from dataclasses import dataclass
from pathlib import Path

MODELS_DIR_NAME = "models"


@dataclass(frozen=True)
class SharedModelsStatus:
    """Whether this node's own real `models/` directory has real content.

    `present` is deliberately about real file content, not just the
    directory existing - an empty `models/` (its checked-out-but-never-
    provisioned state on a dev machine) is honestly reported the same as
    a missing one: no weights are actually available either way.
    """

    present: bool
    path: Path


def check_shared_models(repo_root: Path) -> SharedModelsStatus:
    """Real check of `repo_root/models/` - this node's own shared weights
    directory, not a sibling's. `repo_root` is this repository's own
    root (see `main.py`'s `_REPO_ROOT`), never the workspace root
    `family-status --workspace` scans for sibling checkouts."""
    models_dir = repo_root / MODELS_DIR_NAME
    present = models_dir.is_dir() and any(models_dir.iterdir())
    return SharedModelsStatus(present=present, path=models_dir)
