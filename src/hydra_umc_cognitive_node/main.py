# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Entry point for HYDRA-UMC-COGNITIVE-NODE.

Bare invocation prints identity/version/role, unchanged from the
scaffolding stage. The real v0 work lives behind the `family-status`
subcommand: a real readiness check of this node's four real children,
reading each sibling's own hydra-umc.project.json - not the real
LLM/VLA/voice orchestration the README's own roadmap describes, which
this integration hub was never meant to run itself.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .api import CognitiveNodeServer
from .family import check_family_status, family_status_to_dict
from .models import check_shared_models

PROJECT_NAME = "HYDRA-UMC-COGNITIVE-NODE"
ROLE = (
    "Semantic reasoning & GenAI edge node (Hailo-10) - integrates "
    "VLA-Engine, Voice-UI, Semantic-Planner and Docs-QA into one "
    "cognitive node."
)

# This file lives at src/hydra_umc_cognitive_node/main.py - two parents
# up is this repo's own root, and one more level up is the workspace
# that holds it as a sibling of the other ecosystem repos.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_WORKSPACE = _REPO_ROOT.parent


def _print_identity() -> None:
    print(f"{PROJECT_NAME} v{__version__}")
    print(ROLE)


def _run_family_status(workspace: Path, *, as_json: bool) -> int:
    statuses = check_family_status(workspace)
    shared_models = check_shared_models(_REPO_ROOT)

    if as_json:
        print(json.dumps(family_status_to_dict(statuses, shared_models), indent=2))
        return 0 if all(status.present for status in statuses) else 1

    print(f"Cognitive AI Node family status (workspace: {workspace}):")
    for status in statuses:
        if not status.present or status.manifest is None:
            print(f"  {status.name}: NOT FOUND")
            continue
        m = status.manifest
        print(f"  {status.name}: v{m.version}, maturity={m.maturity}, role={m.role}")

    if shared_models.present:
        print(f"\nShared model weights: present ({shared_models.path})")
    else:
        print(
            f"\nShared model weights: MISSING ({shared_models.path}) - "
            "this node's own os/models weights have not been provisioned "
            "on this machine; children that need them will run in their "
            "own honest degraded/no-hardware mode."
        )

    missing = [status.name for status in statuses if not status.present]
    if missing:
        print(f"\n{len(missing)} of {len(statuses)} children not found: {', '.join(missing)}")
        return 1
    print(f"\nAll {len(statuses)} children present.")
    return 0


def _run_serve(addr: str, port: int, workspace: Path) -> int:
    server = CognitiveNodeServer((addr, port), workspace, _REPO_ROOT)
    print(f"[cognitive-node] HTTP API listening on {addr}:{port} (workspace={workspace})")
    print("[cognitive-node] GET /family-status, GET /stats")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[cognitive-node] shutting down")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hydra-umc-cognitive-node", description=ROLE)
    subparsers = parser.add_subparsers(dest="command")

    family_parser = subparsers.add_parser(
        "family-status", help="Real readiness check of this node's four real children."
    )
    family_parser.add_argument(
        "--workspace",
        type=Path,
        default=_DEFAULT_WORKSPACE,
        help="Directory containing the sibling repo checkouts (default: this repo's own parent directory).",
    )
    family_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a real, versioned machine-readable result instead of the human-readable table.",
    )

    serve_parser = subparsers.add_parser(
        "serve",
        help="Run family-status as a JSON/HTTP API (GET /family-status) - the exact "
             "same function 'family-status --json' already runs.",
    )
    serve_parser.add_argument("--addr", default="127.0.0.1", help="address to bind the HTTP API to")
    serve_parser.add_argument("--port", type=int, default=8096, help="port for the HTTP API")
    serve_parser.add_argument(
        "--workspace",
        type=Path,
        default=_DEFAULT_WORKSPACE,
        help="Default workspace for GET /family-status when it is not overridden per-request.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "family-status":
        return _run_family_status(args.workspace, as_json=args.json)
    if args.command == "serve":
        return _run_serve(args.addr, args.port, args.workspace)

    _print_identity()
    return 0


if __name__ == "__main__":
    sys.exit(main())
