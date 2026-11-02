# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
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
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .access import bind_warning, is_loopback, load_token
from .api import CognitiveNodeServer
from .autonomy import AutonomyPolicy, load_autonomy_config
from .family_mqtt import FamilyPublisher, load_mqtt_config
from .npu import NpuScheduler, load_npu_config
from .family import check_family_status, env_versions, family_status_to_dict
from .llm import Narrator, load_llm_config, make_backend
from .models import check_shared_models
from .probe import health_to_dict, probe_family

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
_DEFAULT_WORKSPACE = Path(os.environ.get("HYDRA_UMC_COGNITIVE_NODE_WORKSPACE") or _REPO_ROOT.parent)
# After `pip install` the package lives in site-packages, so the repository-relative
# defaults above point nowhere; a container passes these explicitly.
_DEFAULT_MODELS_DIR = os.environ.get("HYDRA_UMC_COGNITIVE_NODE_MODELS_DIR")


def _print_identity() -> None:
    print(f"{PROJECT_NAME} v{__version__}")
    print(ROLE)


def _run_family_status(workspace: Path, *, as_json: bool, models_dir: Path | None = None, probe: bool = False) -> int:
    statuses = check_family_status(workspace)
    shared_models = check_shared_models(_REPO_ROOT, models_dir)
    health = None
    if probe:
        try:
            health = {h.name: health_to_dict(h) for h in probe_family(workspace)}
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

    if as_json:
        print(json.dumps(family_status_to_dict(statuses, shared_models, health), indent=2))
        if health is not None and not all((health.get(s.name) or {}).get("healthy") is True for s in statuses):
            return 1
        return 0 if all(status.present for status in statuses) else 1

    print(f"Cognitive AI Node family status (workspace: {workspace}):")
    for status in statuses:
        if not status.present or status.manifest is None:
            print(f"  {status.name}: NOT FOUND")
            continue
        m = status.manifest
        line = f"  {status.name}: v{m.version}, maturity={m.maturity}, role={m.role}"
        if health is not None:
            h = health[status.name]
            if not h["reachable"]:
                line += f" - NOT ANSWERING at {h['url']} ({h['error']})"
            else:
                state = {True: "healthy", False: "UNHEALTHY", None: "answers"}[h["healthy"]]
                line += f" - {state} (HTTP {h['http_status']}, {h['latency_ms']} ms)"
        print(line)

    if shared_models.present:
        print(f"\nShared model weights: present ({shared_models.path})")
    else:
        print(
            f"\nShared model weights: MISSING ({shared_models.path}) - "
            "this node's own os/models weights have not been provisioned "
            "on this machine; children that need them will run in their "
            "own honest degraded/no-hardware mode."
        )

    if health is not None:
        unwell = [s.name for s in statuses if (health.get(s.name) or {}).get("healthy") is not True]
        if unwell:
            print(f"\n{len(unwell)} of {len(statuses)} children are not answering well: {', '.join(unwell)}")
            return 1

    missing = [status.name for status in statuses if not status.present]
    if missing:
        print(f"\n{len(missing)} of {len(statuses)} children not found: {', '.join(missing)}")
        return 1
    print(f"\nAll {len(statuses)} children present.")
    return 0


def _run_serve(addr: str, port: int, workspace: Path, models_dir: Path | None = None, token_file: str | None = None, max_threads: int = 32, llm_config: str | None = None,
               autonomy_config: str | None = None, npu_config: str | None = None, mqtt_config: str | None = None) -> int:
    try:
        token = load_token(token_file)
        narrator = None
        scheduler = None
        autonomy = None
        publisher = None
        if npu_config:
            npu = load_npu_config(npu_config)
            if npu.enabled:
                scheduler = NpuScheduler(npu)
        if llm_config:
            config = load_llm_config(llm_config)
            if config.enabled:
                if scheduler is not None and "llm" not in scheduler.config.consumers:
                    raise ValueError('the npu configuration has no consumer "llm", which the language model needs')
                narrator = Narrator(config, make_backend(config), scheduler)
        if autonomy_config:
            policy_config = load_autonomy_config(autonomy_config)
            if policy_config.enabled:
                if not token and not is_loopback(addr):
                    raise ValueError("the autonomy policy answers whether an AI output may move hardware: it needs a bearer token (--token-file) when the address is not loopback")
                autonomy = AutonomyPolicy(policy_config)
        if mqtt_config:
            mqtt = load_mqtt_config(mqtt_config)
            if mqtt.enabled:
                def snapshot(probe: bool) -> dict[str, Any]:
                    statuses = check_family_status(workspace)
                    health = {h.name: health_to_dict(h) for h in probe_family(workspace)} if probe else None
                    return family_status_to_dict(statuses, check_shared_models(_REPO_ROOT, models_dir), health)
                publisher = FamilyPublisher(mqtt, snapshot)
        server = CognitiveNodeServer((addr, port), workspace, _REPO_ROOT, models_dir, token, max_threads, narrator, autonomy, scheduler, publisher)
    except ValueError as error:
        print(f"[cognitive-node] error: {error}", file=sys.stderr)
        return 2
    warning = bind_warning(addr, token)
    if warning:
        print(f"[cognitive-node] warning: {warning}", file=sys.stderr)
    print(f"[cognitive-node] HTTP API listening on {addr}:{port} (workspace={workspace}; {'Bearer token required except on /stats' if token else 'no token'})")
    print("[cognitive-node] GET /family-status, GET /stats" + (f", POST /narrative (language model: {narrator.backend.name})" if narrator is not None else ""))
    if autonomy is not None:
        print("[cognitive-node] POST /autonomy/evaluate, GET /autonomy/policy, GET /autonomy/audit (autonomy policy on)")
    if scheduler is not None:
        print(f"[cognitive-node] POST /npu/acquire, POST /npu/release, GET /npu (budget of the accelerator: {scheduler.config.slots} slot(s); no device is opened by this node for it)")
    if publisher is not None:
        print(f"[cognitive-node] the family goes to the retained topic {publisher.config.topic} on {publisher.config.broker}")
        publisher.start()
    if narrator is not None and narrator.backend.name == "simulator":
        print("[cognitive-node] the language model is a SIMULATOR: the texts come from a template, not from a model")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if publisher is not None:
            publisher.stop()
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
        help="Directory containing the sibling repo checkouts (default: $HYDRA_UMC_COGNITIVE_NODE_WORKSPACE, "
             "else this repo's own parent directory).",
    )
    family_parser.add_argument(
        "--models-dir",
        type=Path,
        default=_DEFAULT_MODELS_DIR,
        help="Shared model weights directory (default: $HYDRA_UMC_COGNITIVE_NODE_MODELS_DIR, else this repo's models/).",
    )
    family_parser.add_argument(
        "--probe",
        action="store_true",
        help="Also ask each running child for its health (GET to the route its manifest declares). Where the children are: "
             "the loopback ports of their systemd units, or $HYDRA_UMC_COGNITIVE_NODE_CHILD_URLS (NAME=URL,...). "
             "Without it only the manifests are read.",
    )
    family_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a real, versioned machine-readable result instead of the human-readable table.",
    )

    versions_parser = subparsers.add_parser(
        "family-versions",
        help="Print HYDRA_UMC_<CHILD>_VERSION=x.y.z lines (from the manifests of the checkouts) for the .env file of docker-compose.yml.",
    )
    versions_parser.add_argument("--workspace", type=Path, default=_DEFAULT_WORKSPACE)

    serve_parser = subparsers.add_parser(
        "serve",
        help="Run family-status as a JSON/HTTP API (GET /family-status) - the exact "
             "same function 'family-status --json' already runs.",
    )
    serve_parser.add_argument("--addr", default="127.0.0.1", help="address to bind the HTTP API to")
    serve_parser.add_argument("--port", type=int, default=8096, help="port for the HTTP API")
    serve_parser.add_argument("--token-file", default=None, help="File with the bearer token every route but GET /stats must present (or the HYDRA_UMC_COGNITIVE_NODE_TOKEN environment variable); off by default")
    serve_parser.add_argument("--max-threads", type=int, default=32, help="Requests handled at the same time, 1 to 1024; one more answers 503 at once (default: 32)")
    serve_parser.add_argument("--llm-config", default=os.environ.get("HYDRA_UMC_COGNITIVE_NODE_LLM_CONFIG"), help="JSON file that switches on POST /narrative, the local language model for trend summaries (see docs/NARRATIVE.md); off by default (or the HYDRA_UMC_COGNITIVE_NODE_LLM_CONFIG environment variable)")
    serve_parser.add_argument("--autonomy-config", default=os.environ.get("HYDRA_UMC_COGNITIVE_NODE_AUTONOMY_CONFIG"), help="JSON file that switches on the autonomy policy (POST /autonomy/evaluate, see docs/AUTONOMY.md); off by default (or the HYDRA_UMC_COGNITIVE_NODE_AUTONOMY_CONFIG environment variable)")
    serve_parser.add_argument("--npu-config", default=os.environ.get("HYDRA_UMC_COGNITIVE_NODE_NPU_CONFIG"), help="JSON file that switches on the budget of the accelerator (POST /npu/acquire, see docs/NPU_BUDGET.md); off by default (or the HYDRA_UMC_COGNITIVE_NODE_NPU_CONFIG environment variable)")
    serve_parser.add_argument("--mqtt-config", default=os.environ.get("HYDRA_UMC_COGNITIVE_NODE_MQTT_CONFIG"), help="JSON file that switches on the state of the family on a retained MQTT topic (see docs/FAMILY_MQTT.md); off by default (or the HYDRA_UMC_COGNITIVE_NODE_MQTT_CONFIG environment variable)")
    serve_parser.add_argument(
        "--workspace",
        type=Path,
        default=_DEFAULT_WORKSPACE,
        help="Workspace scanned by GET /family-status (default: $HYDRA_UMC_COGNITIVE_NODE_WORKSPACE, "
             "else this repo's own parent directory). Fixed at startup; requests cannot change it.",
    )
    serve_parser.add_argument(
        "--models-dir",
        type=Path,
        default=_DEFAULT_MODELS_DIR,
        help="Shared model weights directory (default: $HYDRA_UMC_COGNITIVE_NODE_MODELS_DIR, else this repo's models/).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "family-status":
        return _run_family_status(args.workspace, as_json=args.json, models_dir=args.models_dir, probe=args.probe)
    if args.command == "family-versions":
        for line in env_versions(check_family_status(args.workspace)):
            print(line)
        return 0
    if args.command == "serve":
        return _run_serve(args.addr, args.port, args.workspace, args.models_dir, args.token_file, args.max_threads, args.llm_config,
                          args.autonomy_config, args.npu_config, args.mqtt_config)

    _print_identity()
    return 0


if __name__ == "__main__":
    sys.exit(main())
