# HYDRA-UMC-COGNITIVE-NODE — CLI Reference

`hydra-umc-cognitive-node` is a Python console script
(`src/hydra_umc_cognitive_node/main.py`, installed as an entry point via
`pyproject.toml`). This repo is the Cognitive AI Node family's
integration hub — it owns the shared HydraOS image/model weights and the
`docker-compose.yml` wiring, but runs no model itself. The one real v0
command it ships, `family-status`, checks whether its four real children
are actually present on disk and what maturity they've really reached,
by reading each sibling's own `hydra-umc.project.json` — the same
manifest the ecosystem-wide dashboard and updater already trust, rather
than a second hand-maintained list. Every example below was captured
from a real run of the installed CLI — not written from memory.

## Usage

```
$ hydra-umc-cognitive-node -h
usage: hydra-umc-cognitive-node [-h] {family-status} ...

Semantic reasoning & GenAI edge node (Hailo-10) - integrates VLA-Engine,
Voice-UI, Semantic-Planner and Docs-QA into one cognitive node.

positional arguments:
  {family-status}
    family-status  Real readiness check of this node's four real children.

options:
  -h, --help       show this help message and exit
```

Bare invocation (no subcommand) prints identity/version/role and exits `0`:

```
$ hydra-umc-cognitive-node
HYDRA-UMC-COGNITIVE-NODE v0.0.5
Semantic reasoning & GenAI edge node (Hailo-10) - integrates VLA-Engine, Voice-UI, Semantic-Planner and Docs-QA into one cognitive node.
```

## Commands

### `family-status [--workspace PATH]`

```
$ hydra-umc-cognitive-node family-status -h
usage: hydra-umc-cognitive-node family-status [-h] [--workspace WORKSPACE]

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Directory containing the sibling repo checkouts
                        (default: this repo's own parent directory).
```

The four expected children are declared once, in `family.py`:
`HYDRA-UMC-VLA-ENGINE`, `HYDRA-UMC-VOICE-UI`,
`HYDRA-UMC-SEMANTIC-PLANNER`, `HYDRA-UMC-DOCS-QA`. Each one's own
`hydra-umc.project.json` is read defensively — missing file, malformed
JSON, or a missing field all degrade to "not found", never a crash.

**Real run** against this machine's actual GitHub workspace (all four
siblings really checked out):

```
$ hydra-umc-cognitive-node family-status
Cognitive AI Node family status (workspace: C:\Users\juane\Documents\GitHub):
  HYDRA-UMC-VLA-ENGINE: v0.0.4, maturity=functional, role=service
  HYDRA-UMC-VOICE-UI: v0.0.5, maturity=functional, role=service
  HYDRA-UMC-SEMANTIC-PLANNER: v0.0.4, maturity=functional, role=service
  HYDRA-UMC-DOCS-QA: v0.0.5, maturity=established, role=api

All 4 children present.
$ echo $?
0
```

**Real miss** — pointing `--workspace` at a real, empty directory (none
of the four children checked out there):

```
$ hydra-umc-cognitive-node family-status --workspace /path/to/empty-dir
Cognitive AI Node family status (workspace: /path/to/empty-dir):
  HYDRA-UMC-VLA-ENGINE: NOT FOUND
  HYDRA-UMC-VOICE-UI: NOT FOUND
  HYDRA-UMC-SEMANTIC-PLANNER: NOT FOUND
  HYDRA-UMC-DOCS-QA: NOT FOUND

4 of 4 children not found: HYDRA-UMC-VLA-ENGINE, HYDRA-UMC-VOICE-UI, HYDRA-UMC-SEMANTIC-PLANNER, HYDRA-UMC-DOCS-QA
$ echo $?
1
```

A workspace with some but not all children present prints the same
per-child lines (a mix of `NOT FOUND` and real `vX.Y.Z, maturity=...,
role=...` lines) and still exits `1` — any missing child is a real
failure for this command, not merely informational.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | all four expected children found and readable |
| `1` | one or more expected children missing (not checked out, or manifest missing/unreadable) |

## Not yet a real orchestrator

`family-status` is deliberately the *only* real subcommand today. The
actual LLM/VLA/voice orchestration described in this repo's own README
roadmap is not implemented here — this integration hub coordinates the
`docker-compose.yml` wiring for its children, it does not run a model
itself.
