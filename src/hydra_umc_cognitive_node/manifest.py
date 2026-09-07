# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/manifest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real, minimal reader for a sibling repository's own hydra-umc.project.json.

Deliberately a small local reader, not a dependency on
HYDRA-UMC-UPDATER's own full project_manifest.py validator (that lives in
a different repository) - this only needs the handful of fields the
family status check actually displays, read defensively so a missing or
malformed sibling manifest degrades to "not found", never a crash.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

MANIFEST_FILE = "hydra-umc.project.json"

# A real hydra-umc.project.json across this whole ecosystem is a few
# hundred bytes to a couple of KiB (see any sibling's own manifest). This
# is a generous real resource limit, not a tight one: it exists so that
# a corrupted or malicious sibling checkout (a manifest replaced by a
# multi-gigabyte file, accidentally or otherwise) can never make a
# routine family-status check read an unbounded amount of data into
# memory - it degrades to "not found", the same as any other malformed
# manifest, rather than hanging or exhausting memory.
MAX_MANIFEST_BYTES = 64 * 1024


@dataclass(frozen=True)
class ChildManifest:
    name: str
    version: str
    maturity: str
    role: str


def read_child_manifest(repo_path: Path) -> ChildManifest | None:
    """Read `repo_path/hydra-umc.project.json` for real, or return None.

    None covers every real reason this can fail - the sibling isn't
    checked out, its manifest is missing, is larger than
    MAX_MANIFEST_BYTES, or is malformed JSON/missing a field - callers
    treat all of these as "not ready", not an error.
    """
    manifest_path = repo_path / MANIFEST_FILE
    if not manifest_path.is_file():
        return None
    try:
        if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
            return None
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        required = ("name", "version", "maturity", "role")
        if any(not isinstance(data.get(field), str) or not data[field].strip() for field in required):
            return None
        return ChildManifest(
            name=data["name"],
            version=data["version"],
            maturity=data["maturity"],
            role=data["role"],
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None
