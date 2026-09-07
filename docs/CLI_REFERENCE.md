# HYDRA-UMC-COGNITIVE-NODE — CLI Reference

`hydra-umc-cognitive-node` is a Python console script
(`src/hydra_umc_cognitive_node/main.py`, installed as an entry point via
`pyproject.toml`). This repo is the Cognitive AI Node family's
integration hub — it owns the shared HydraOS image/model weights and the
`docker-compose.yml` wiring, but runs no model itself. The two real v0
commands it ships are `family-status` — checks whether its four real
children are actually present on disk and what maturity they've really
reached, by reading each sibling's own `hydra-umc.project.json`, the
same manifest the ecosystem-wide dashboard and updater already trust,
rather than a second hand-maintained list — and `serve`, which exposes
that exact same check over a small stdlib HTTP API; it is what the real
`hydra-umc-cognitive-node.service` systemd unit runs on the CM5. Every
example below was captured from a real run of the installed CLI — not
written from memory.

## Usage

```
$ hydra-umc-cognitive-node -h
usage: hydra-umc-cognitive-node [-h] {family-status,serve} ...

Semantic reasoning & GenAI edge node (Hailo-10) - integrates VLA-Engine,
Voice-UI, Semantic-Planner and Docs-QA into one cognitive node.

positional arguments:
  {family-status,serve}
    family-status       Real readiness check of this node's four real
                        children.
    serve               Run family-status as a JSON/HTTP API (GET /family-
                        status) - the exact same function 'family-status
                        --json' already runs.

options:
  -h, --help            show this help message and exit
```

Bare invocation (no subcommand) prints identity/version/role and exits `0`:

```
$ hydra-umc-cognitive-node
HYDRA-UMC-COGNITIVE-NODE v0.0.8
Semantic reasoning & GenAI edge node (Hailo-10) - integrates VLA-Engine, Voice-UI, Semantic-Planner and Docs-QA into one cognitive node.
```

## Commands

### `family-status [--workspace PATH] [--json]`

```
$ hydra-umc-cognitive-node family-status -h
usage: hydra-umc-cognitive-node family-status [-h] [--workspace WORKSPACE]
                                              [--json]

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Directory containing the sibling repo checkouts
                        (default: this repo's own parent directory).
  --json                Print a real, versioned machine-readable result
                        instead of the human-readable table.
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
  HYDRA-UMC-VLA-ENGINE: v0.1.0, maturity=established, role=service
  HYDRA-UMC-VOICE-UI: v0.1.0, maturity=established, role=service
  HYDRA-UMC-SEMANTIC-PLANNER: v0.0.7, maturity=established, role=service
  HYDRA-UMC-DOCS-QA: v0.0.7, maturity=established, role=api

Shared model weights: MISSING (C:\Users\juane\Documents\GitHub\HYDRA-UMC-COGNITIVE-NODE\models) - this node's own os/models weights have not been provisioned on this machine; children that need them will run in their own honest degraded/no-hardware mode.

All 4 children present.
$ echo $?
0
```

Every real run also reports this node's own shared model weights (see
"Shared-model readiness criterion" below) — a real, empty `models/` on a
dev machine is honestly `MISSING`, never silently skipped.

**Real miss** — pointing `--workspace` at a real, empty directory (none
of the four children checked out there):

```
$ hydra-umc-cognitive-node family-status --workspace /path/to/empty-dir
Cognitive AI Node family status (workspace: /path/to/empty-dir):
  HYDRA-UMC-VLA-ENGINE: NOT FOUND
  HYDRA-UMC-VOICE-UI: NOT FOUND
  HYDRA-UMC-SEMANTIC-PLANNER: NOT FOUND
  HYDRA-UMC-DOCS-QA: NOT FOUND

Shared model weights: MISSING (/path/to/HYDRA-UMC-COGNITIVE-NODE/models) - this node's own os/models weights have not been provisioned on this machine; children that need them will run in their own honest degraded/no-hardware mode.

4 of 4 children not found: HYDRA-UMC-VLA-ENGINE, HYDRA-UMC-VOICE-UI, HYDRA-UMC-SEMANTIC-PLANNER, HYDRA-UMC-DOCS-QA
$ echo $?
1
```

A workspace with some but not all children present prints the same
per-child lines (a mix of `NOT FOUND` and real `vX.Y.Z, maturity=...,
role=...` lines) and still exits `1` — any missing child is a real
failure for this command, not merely informational.

`--json` prints the exact same real data as a versioned, machine-readable
object instead of the table above:

```
$ hydra-umc-cognitive-node family-status --json
{
  "schema_version": "1.0",
  "shared_models": {
    "present": false,
    "path": "models"
  },
  "children": [
    {
      "name": "HYDRA-UMC-VLA-ENGINE",
      "present": true,
      "version": "0.1.0",
      "maturity": "established",
      "role": "service"
    },
    {
      "name": "HYDRA-UMC-VOICE-UI",
      "present": true,
      "version": "0.1.0",
      "maturity": "established",
      "role": "service"
    },
    {
      "name": "HYDRA-UMC-SEMANTIC-PLANNER",
      "present": true,
      "version": "0.0.7",
      "maturity": "established",
      "role": "service"
    },
    {
      "name": "HYDRA-UMC-DOCS-QA",
      "present": true,
      "version": "0.0.7",
      "maturity": "established",
      "role": "api"
    }
  ],
  "all_children_present": true
}
$ echo $?
0
```

`--json` still exits `1` when `all_children_present` is `false`, exactly
like the human-readable table.

### `serve [--addr ADDR] [--port PORT] [--workspace PATH]`

```
$ hydra-umc-cognitive-node serve -h
usage: hydra-umc-cognitive-node serve [-h] [--addr ADDR] [--port PORT]
                                      [--workspace WORKSPACE]

options:
  -h, --help            show this help message and exit
  --addr ADDR           address to bind the HTTP API to
  --port PORT           port for the HTTP API
  --workspace WORKSPACE
                        Default workspace for GET /family-status when it is
                        not overridden per-request.
```

`serve` runs a plain stdlib `http.server` (`api.py`, no framework
dependency) that exposes `family-status`'s own logic over HTTP instead of
the CLI — `GET /family-status` reaches the exact same
`check_family_status()`/`family_status_to_dict()` functions `family-status
--json` already runs, so the JSON shape is identical to the block above.
This is the real command the CM5's own `hydra-umc-cognitive-node.service`
systemd unit runs in production
(`serve --addr 127.0.0.1 --port 8096 --workspace /opt/hydra-umc/cognitive-node/workspace`).

Real captured responses from a locally started server:

```
$ hydra-umc-cognitive-node serve --port 8096 &
[cognitive-node] HTTP API listening on 127.0.0.1:8096 (workspace=..)
[cognitive-node] GET /family-status, GET /stats

$ curl -s http://127.0.0.1:8096/family-status
{"schema_version": "1.0", "shared_models": {"present": false, "path": "models"}, "children": [{"name": "HYDRA-UMC-VLA-ENGINE", "present": true, "version": "0.1.0", "maturity": "established", "role": "service"}, {"name": "HYDRA-UMC-VOICE-UI", "present": true, "version": "0.1.0", "maturity": "established", "role": "service"}, {"name": "HYDRA-UMC-SEMANTIC-PLANNER", "present": true, "version": "0.0.7", "maturity": "established", "role": "service"}, {"name": "HYDRA-UMC-DOCS-QA", "present": true, "version": "0.0.7", "maturity": "established", "role": "api"}], "all_children_present": true}

$ curl -s http://127.0.0.1:8096/stats
{"workspace": ".."}

$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8096/nope
404
```

`GET /family-status` accepts an optional `?workspace=` query parameter
to override the server's default per-request. A repeated query parameter
(e.g. `?workspace=a&workspace=b`) is rejected with `400` rather than
silently taking one value. `GET /stats` reports only the server's
configured default workspace path — it does not itself run the
family-status check. Any other path returns `404`. The handler is quiet
by default (no per-request access log line), matching this family's
other `api.py` modules.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | `family-status`: all four expected children found and readable |
| `1` | `family-status`: one or more expected children missing (not checked out, or manifest missing/unreadable) |

`serve` runs until interrupted (`Ctrl+C`) and always exits `0` on a clean
shutdown; individual HTTP requests report success/failure through their
own status code (`200`/`400`/`404`), never through the process exit code.

## Not yet a real orchestrator

`family-status` and `serve` are deliberately the *only* real subcommands
today. The actual LLM/VLA/voice orchestration described in this repo's
own README roadmap is not implemented here — this integration hub
coordinates the `docker-compose.yml` wiring for its children, it does
not run a model itself.

## Shared-model readiness criterion

The `shared_models.present` field is deliberately conservative. It is `true`
only when this repository's own `models/` tree contains a non-empty local
candidate artifact with an expected weight extension (`.hef`, `.har`, `.bin`,
`.onnx`, `.tflite`, `.gguf`, or `.safetensors`). Empty directories, `.gitkeep`,
documentation, tokenizers, and configuration-only trees remain `false`.
Symlinks are ignored so a local readiness check cannot escape this repository's
models tree. This is an inventory signal only: a real Hailo-10 runtime still
has to validate artifact compatibility on the physical target.
