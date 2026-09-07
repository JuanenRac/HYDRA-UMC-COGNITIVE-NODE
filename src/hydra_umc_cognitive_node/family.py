# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/family.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real family-readiness check: this node's actual job today.

This repository is the Cognitive AI Node family's integration hub - it
owns the shared HydraOS image/model weights and the docker-compose.yml
wiring, but runs no model itself (see the README's own Architecture
section). A real v0 for an integration hub that doesn't run a model yet
is checking whether its real children are actually present and what
maturity they've really reached - reading each sibling's own real
hydra-umc.project.json, the same manifest the ecosystem-wide dashboard
and updater already trust, rather than a second hand-maintained list.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import ChildManifest, read_child_manifest
from .models import SharedModelsStatus

# The four real children this node's own README and docker-compose.yml
# both name - kept here as the one place this project declares them.
EXPECTED_CHILDREN: tuple[str, ...] = (
    "HYDRA-UMC-VLA-ENGINE",
    "HYDRA-UMC-VOICE-UI",
    "HYDRA-UMC-SEMANTIC-PLANNER",
    "HYDRA-UMC-DOCS-QA",
)

# Versions the real, machine-readable shape `family_status_to_dict()`
# below returns - the one real input/output contract this integration
# hub has today (`family-status`'s own request/response shape). Bumped
# only on a real, breaking shape change, the same convention every
# manifest/API contract elsewhere in this ecosystem already uses.
FAMILY_STATUS_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ChildStatus:
    name: str
    present: bool
    manifest: ChildManifest | None


def check_family_status(workspace_root: Path) -> list[ChildStatus]:
    """Real check of every expected child under `workspace_root`.

    `workspace_root` is the directory that contains this repo's own
    checkout as a sibling of the others (e.g. the parent of
    `HYDRA-UMC-COGNITIVE-NODE/` itself) - the same layout every real
    checkout of this ecosystem already uses.
    """
    statuses = []
    for child_name in EXPECTED_CHILDREN:
        manifest = read_child_manifest(workspace_root / child_name)
        statuses.append(ChildStatus(name=child_name, present=manifest is not None, manifest=manifest))
    return statuses


def family_status_to_dict(
    statuses: list[ChildStatus], shared_models: SharedModelsStatus
) -> dict[str, Any]:
    """Real, versioned machine-readable shape for a family-status result -
    the CLI's `--json` output (see `main.py`). Every field here is real
    data this check already computed; nothing is invented for the sake
    of a richer-looking schema."""
    return {
        "schema_version": FAMILY_STATUS_SCHEMA_VERSION,
        "shared_models": {
            "present": shared_models.present,
            "path": str(shared_models.path),
        },
        "children": [
            {
                "name": status.name,
                "present": status.present,
                "version": status.manifest.version if status.manifest else None,
                "maturity": status.manifest.maturity if status.manifest else None,
                "role": status.manifest.role if status.manifest else None,
            }
            for status in statuses
        ],
        "all_children_present": all(status.present for status in statuses),
    }
