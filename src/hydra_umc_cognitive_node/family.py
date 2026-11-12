# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/family.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
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

import json
import os
import re
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


#: The file that says the lowest version of each child this node accepts: `{"HYDRA-UMC-VOICE-UI": "0.2.0", ...}`. Its place is the variable
#: below; with no file nothing is required (the conservative reading of "not configured" is to report the versions and judge none).
MINIMUMS_ENVIRONMENT = "HYDRA_UMC_FAMILY_MINIMUMS"
MAX_MINIMUMS_BYTES = 64 * 1024
_VERSION = re.compile(r"\d+(\.\d+){1,3}")


def parse_version(text: str) -> tuple[int, int, int, int] | None:
    """`1.2.3` or `1.2.3.4` as four numbers (a missing fourth is 0); None for anything else, a pre-release tag included."""
    if not isinstance(text, str) or _VERSION.fullmatch(text.strip()) is None:
        return None
    numbers = [int(part) for part in text.strip().split(".")]
    numbers += [0] * (4 - len(numbers))
    return (numbers[0], numbers[1], numbers[2], numbers[3])


def load_minimum_versions(path: str | None = None, env: dict[str, str] | None = None) -> dict[str, str]:
    """The minimum versions of the file named by [path] (default: the variable). A file that is missing, too large or not an object of
    `name: version` pairs gives no minimums at all; a pair whose version cannot be read is dropped, so one typo never hides the others."""
    chosen = path if path is not None else (env if env is not None else os.environ).get(MINIMUMS_ENVIRONMENT, "")
    if not chosen:
        return {}
    try:
        file = Path(chosen)
        if not file.is_file() or file.stat().st_size > MAX_MINIMUMS_BYTES:
            return {}
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {name: version for name, version in data.items() if isinstance(name, str) and parse_version(version) is not None}


def is_compatible(version: str, minimum: str) -> bool | None:
    """True when [version] is at least [minimum]; None when either cannot be read as a version (nothing can be said)."""
    have, need = parse_version(version), parse_version(minimum)
    if have is None or need is None:
        return None
    return have >= need


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
    statuses: list[ChildStatus],
    shared_models: SharedModelsStatus,
    health: dict[str, dict[str, Any]] | None = None,
    minimums: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Real, versioned machine-readable shape for a family-status result -
    the CLI's `--json` output (see `main.py`). Every field here is real
    data this check already computed; nothing is invented for the sake
    of a richer-looking schema."""
    children = []
    for status in statuses:
        entry: dict[str, Any] = {
            "name": status.name,
            "present": status.present,
            "version": status.manifest.version if status.manifest else None,
            "maturity": status.manifest.maturity if status.manifest else None,
            "role": status.manifest.role if status.manifest else None,
        }
        if minimums:
            # only when a minimum was configured: the version of the child against the lowest this node accepts (None: nothing can be said)
            minimum = minimums.get(status.name)
            entry["minimum_version"] = minimum
            entry["compatible"] = None if minimum is None or status.manifest is None else is_compatible(status.manifest.version, minimum)
        if health is not None:
            # only when the services were asked (see probe.py): what is installed and what is answering are different things
            entry["health"] = health.get(status.name)
        children.append(entry)
    result: dict[str, Any] = {
        "schema_version": FAMILY_STATUS_SCHEMA_VERSION,
        "shared_models": {
            "present": shared_models.present,
            "path": str(shared_models.path),
        },
        "children": children,
        "all_children_present": all(status.present for status in statuses),
    }
    if minimums:
        # False as soon as one child that is present is older than its minimum; a child that is missing is already said by all_children_present
        result["all_children_compatible"] = all(child.get("compatible") is not False for child in children)
    if health is not None:
        result["all_children_healthy"] = all((health.get(status.name) or {}).get("healthy") is True for status in statuses)
    return result


def env_versions(statuses: list[ChildStatus]) -> list[str]:
    """`HYDRA_UMC_<CHILD>_VERSION=x.y.z` lines for the children that have a manifest, for the `.env` file next to docker-compose.yml: the
    images are tagged with these, so a container is the version of the checkout it was built from."""
    lines = []
    for status in statuses:
        if status.manifest is not None:
            key = status.name.removeprefix("HYDRA-UMC-").replace("-", "_")
            lines.append(f"HYDRA_UMC_{key}_VERSION={status.manifest.version}")
    return lines
