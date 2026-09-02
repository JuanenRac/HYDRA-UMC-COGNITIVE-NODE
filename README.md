<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-COGNITIVE-NODE banner" width="100%">
</p>

# 🧠 HYDRA-UMC-COGNITIVE-NODE

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🤖 Semantic Reasoning & GenAI Edge Node (Hailo-10 + Raspberry Pi CM5)

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Hardware-CM5%20%2B%20Hailo--10-orange.svg" alt="CM5 + Hailo-10">
  <img src="https://img.shields.io/badge/Performance-40%20TOPS-green.svg" alt="40 TOPS">
  <img src="https://img.shields.io/badge/GenAI-Local%20LLM%20%2F%20VLA-blueviolet.svg" alt="GenAI">
</p>

---

## 1. 🛠️ TECHNICAL OVERVIEW

**HYDRA-UMC-COGNITIVE-NODE** serves as the "frontal lobe" of the HYDRA-UMC ecosystem. Powered by the Hailo-10 NPU (40 TOPS), it enables complex semantic reasoning, natural language understanding, and vision-language-action (VLA) task planning directly at the edge.

It transforms high-level human instructions into logical robotic sequences, managing error recovery and mission optimization without cloud dependency.

### Key Features:
* 🧠 **Local LLM Execution:** Hardware-accelerated inference for quantized models (Llama/Mistral). *(planned - needs the real Hailo-10 model runtime)*
* 👁️ **VLA Integration:** Vision-Language-Action models for intuitive task execution. *(planned)*
* 🎙️ **Voice Command Processing:** Real-time STT/TTS for human-robot interaction. *(planned)*
* 🛡️ **Privacy First:** 100% offline processing of all cognitive tasks. *(true by design once the above exist - nothing here calls out to a network today)*
* 🧩 **Integration Hub (v0):** Owns the shared HydraOS image and quantized model
  weights consumed by its four children, and wires them together as
  sibling services in a single `docker-compose.yml`. Real `family-status`
  check reads each real child's own manifest to report presence/version/
  maturity. *(implemented as a real readiness check - see BUILD & RUN
  below)*
* 🔒 **Versioned status schema + resource-limited manifest reads:** `family-status --json` prints a real, versioned machine-readable result; any sibling manifest bigger than 64 KiB (a corrupted/malicious checkout) degrades to "not found" instead of being read unbounded. *(implemented)*
* 🪫 **Shared model-weights degradation check:** `family-status` honestly reports whether this node's own `models/` directory actually has real weights in it, not just whether the sibling repos are checked out. *(implemented)*
* 📦 **Odometer Versioning:** Every real build bumps `pyproject.toml`'s
  own version automatically (`bump_version.py`) - no manual version edits.

---

## 2. 🔄 COGNITIVE WORKFLOW

```mermaid
flowchart TB
    INPUT["Voice / Text Input"] --> VOICE["VOICE-UI (STT)"]
    VOICE --> PLANNER["SEMANTIC-PLANNER (LLM)"]
    VIS["Vision Node Data"] --> VLA["VLA-ENGINE"]
    VLA --> PLANNER
    PLANNER --> ORCH["HYDRA-ORCHESTRATOR"]
    DOCS["Technical Manuals"] --> RAG["DOCS-QA (RAG)"]
    RAG --> PLANNER
```

---

## 3. 🧱 ARCHITECTURE & DESIGN DECISIONS

This repository is the **parent/integration point** of the Cognitive AI
Node family. It does not itself run a model - it owns the shared
resources and the wiring that let its four children act as one cognitive
unit on the same physical board:

* **Why this node has no hardware/firmware of its own.** Unlike the
  motherboard-level HYDRA-UMC firmware, this node runs entirely on an
  existing Raspberry Pi CM5 + Hailo-10 M.2 module - there is no custom
  PCB or microcontroller to design here, so `hardware/`/`firmware/`
  folders were pruned rather than left empty.
* **Why `os/` and `models/` live only in the parent.** The HydraOS image
  and the quantized LLM/VLA weights are shared, board-level resources -
  keeping one copy in the parent and mounting it read-only into each
  child's container (see `docker-compose.yml`) avoids four divergent
  copies of multi-gigabyte model weights.
* **Why a `src/` layout.** Keeps the installable package
  (`hydra_umc_cognitive_node`) separate from repo-root tooling
  (`bump_version.py`, `docker-compose.yml`), and matches the layout used
  by every other Python project across the ecosystem.
* **Why the entry point only prints identity/version/role today.** This
  is the andamiaje (scaffolding) stage: proving the package installs,
  compiles and imports cleanly - on the actual target Python version - is
  a prerequisite for adding real LLM/VLA/voice orchestration logic later,
  and keeps that later work isolated from packaging concerns.
* **Why `docker-compose.yml` exists before the children have
  Dockerfiles.** Deciding and documenting the integration contract (which
  service depends on which, what device/volume mounts each needs) now
  avoids that shape being invented ad hoc later, even though `docker
  compose up` cannot fully succeed until each child publishes its own
  Dockerfile.
* **How this fits the rest of the ecosystem.** This node sits one layer
  above perception (HYDRA-UMC-VISION-NODE, Hailo-8) and one layer below
  mission orchestration (HYDRA-UMC-ORCHESTRATOR): it turns voice/text
  instructions and detections into semantic decisions, which the
  orchestrator then turns into physical robot commands.
* **Why `family-status` reads each child's own manifest instead of a
  hand-maintained list.** `hydra-umc.project.json` is already the single
  source of truth the ecosystem-wide dashboard and updater trust - a second
  list here would drift the moment
  a child's real maturity changed and nobody remembered to update it.
* **Why a missing sibling checkout is a real, honest "not found", not an
  error.** An integration hub genuinely doesn't know whether a developer
  has checked out all four children locally - `manifest.py` returns
  `None` for every real failure mode (missing repo, missing manifest,
  malformed JSON) so `family-status` reports it plainly instead of
  crashing.
* **Why sibling manifest reads are capped at 64 KiB.** Every real manifest
  across this ecosystem is a few hundred bytes to a couple of KiB - a
  corrupted or malicious checkout whose manifest has been replaced by an
  oversized file must never make a routine readiness check load an
  unbounded amount of data into memory. It degrades to `None`, the same
  as any other malformed manifest.
* **Why `family-status` reports `models/` even though this node runs no
  model itself.** "The sibling repos are checked out" and "the shared
  weights they'd need are actually present" are two different real
  facts - `models.py`'s `check_shared_models()` checks the second
  honestly (empty-but-present counts as missing) instead of letting an
  operator assume readiness from child presence alone.

---

## 📂 DIRECTORY STRUCTURE

```text
HYDRA-UMC-COGNITIVE-NODE/
├── src/hydra_umc_cognitive_node/
│   ├── manifest.py                 # Real, defensive reader for a sibling's own manifest (64 KiB bound)
│   ├── models.py                   # Real check of this node's own shared model-weights directory
│   ├── family.py                    # Real family-readiness check + versioned JSON schema
│   └── main.py                        # Entry point + real `family-status [--json]` subcommand
├── tests/                          # Real tests: manifest reading, models, family status, end-to-end CLI
├── docs/                           # Documentation and architecture
├── os/                             # HydraOS image/configuration for the CM5
├── models/                         # Hailo-10 optimized weights (LLM/VLA, shared by the 4 children)
├── images/                         # Media and diagrams
├── scripts/                        # Utility scripts
├── build/                          # Local build output (git-ignored)
├── pyproject.toml                  # Package metadata (version odometer-bumped on every real build)
├── bump_version.py                 # Odometer-style version bump (used by build.sh/.bat)
├── docker-compose.yml              # Integration map for the 4 child services
├── build.sh / build.bat            # Create venv, install (with dev extras), run tests, verify import
└── run.sh / run.bat                # Run the entry point (forwards args, e.g. `family-status`)
```

> **Note:** `hardware/` and `firmware/` were pruned - this node runs on an
> existing CM5 + Hailo-10 M.2 module with no hardware/firmware design of
> its own. A dedicated auxiliary microcontroller may be added later if it
> becomes necessary.

---

## ⚙️ BUILD & RUN GUIDE

Requires Python >= 3.10.

```bash
# Linux / macOS / Git Bash
./build.sh   # creates .venv, installs the package (editable), verifies import
./run.sh     # runs the entry point

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` bump the version (odometer-style, see
`bump_version.py`) before every real build, and run the real test suite
(`pytest tests/`). Expected output of a bare `run.sh`:

```text
HYDRA-UMC-COGNITIVE-NODE v0.0.8
Semantic reasoning & GenAI edge node (Hailo-10) - integrates VLA-Engine, Voice-UI, Semantic-Planner and Docs-QA into one cognitive node.
```

See `docker-compose.yml` for how the four child services (VLA-Engine,
Voice-UI, Semantic-Planner, Docs-QA) attach to this node once each ships
its own Dockerfile.

The real `family-status` subcommand checks the real children in a real
local checkout:

```bash
./run.sh family-status
./run.sh family-status --workspace /path/to/some/other/checkout
./run.sh family-status --json

# Windows
run.bat family-status
```

`family-status` always reports this node's own shared model weights
too - a real, empty `models/` on a dev machine is honestly `MISSING`,
never silently ignored:

```text
Cognitive AI Node family status (workspace: /path/to/workspace):
  HYDRA-UMC-VLA-ENGINE: v0.0.4, maturity=functional, role=service
  ...

Shared model weights: MISSING (.../HYDRA-UMC-COGNITIVE-NODE/models) - this node's own os/models weights have not been provisioned on this machine; children that need them will run in their own honest degraded/no-hardware mode.

All 4 children present.
```

`--json` prints the same real data as a versioned, machine-readable
object instead:

```bash
$ ./run.sh family-status --json
{
  "schema_version": "1.0",
  "shared_models": { "present": false, "path": ".../models" },
  "children": [
    { "name": "HYDRA-UMC-VLA-ENGINE", "present": true, "version": "0.0.4", "maturity": "functional", "role": "service" },
    ...
  ],
  "all_children_present": true
}
```

Defaults to this repo's own parent directory - the layout every real
checkout of this ecosystem already uses (all repos as siblings under one
workspace folder). Exits `1` if any real child is missing.

### 🩺 Troubleshooting

* **`python: command not found` / build fails at step 1.** Requires
  Python >= 3.10 on `PATH`. On Windows, install from
  [python.org](https://python.org) and make sure "Add to PATH" was
  checked during setup; `python3` is the usual name on Linux/macOS.
* **`build.sh` fails to activate the venv.** `python3 -m venv .venv`
  lays out the activate script differently per platform:
  `.venv/bin/activate` on Linux/macOS, `.venv/Scripts/activate` on
  Windows (including a Windows Python venv used from Git Bash). `build.sh`
  already checks both paths - if it still fails, delete `.venv/` and
  re-run `./build.sh` to rebuild it from scratch.
* **`pip install -e .` fails.** Usually a stale `.venv/`. Delete the
  `.venv/` folder and re-run `./build.sh`/`build.bat` to recreate it.
* **`import OK` never prints.** Means `python -c "import
  hydra_umc_cognitive_node"` itself failed - re-run with the venv active
  to see the real traceback (a broken `pyproject.toml` edit is the usual
  cause after a manual merge).
* **`docker compose up` does nothing useful.** Expected for now - the
  four child services referenced in `docker-compose.yml` do not have
  published Dockerfiles yet (each currently only ships a Python entry
  point). Run each service directly with its own `run.sh`/`run.bat`
  during development instead.

---

## 🚀 ROADMAP
* **Phase 1:** VLA engine deployment and multi-modal input processing on Hailo-10.
* **Phase 2:** Semantic planner integration with swarm behavioral models and long-term memory.
* **Phase 3:** Voice UI low-latency local execution and industrial noise cancellation.
* **Phase 4:** Autonomous decision-making audits and full integration with Dashboard AI for "See and Ask" feedback.

---

## 🔗 RELATED PROJECTS

This project is part of a larger robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D), spanning firmware, control software, AI nodes, and fleet tooling.

### Family

This node is the Integration Hub (v0) for the 4 services below: it owns the shared HydraOS image and quantized model weights, wires them together in a single `docker-compose.yml`, and checks their presence/version/maturity via `family-status`.

**Children:**
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — STT/TTS gateway; the voice input this node's cognitive workflow starts from.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — the LLM planner that turns this node's inputs into mission decisions.
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — turns vision-node data into action tokens this node's planner consumes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — RAG assistant that grounds this node's planning in technical manuals.

### Directly Related to This Node

- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — gives this node its mission orders.
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — this node consumes its detections.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** / **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — voice-control surfaces for this node.

### Rest of the Ecosystem

**HYDRA-UMC platform** — the multi-robot micro-factory cell
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the motherboard itself: Raspberry Pi CM5 host + dual-core STM32H745 real-time co-processor, orchestrating up to 8 distributed robot arms over CAN-OTA/SPI-OTA.
- **[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — headless Express/WebSocket backend that owns robot state.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — Android control app for HYDRA-UMC.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app for HYDRA-UMC.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop swarm command center.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor.

**URTC platform** — the tool head controller every HYDRA-UMC robot arm carries
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller firmware.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — desktop CAN-OTA + SWD/JTAG flashing tool.
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool.
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to the 2 desktop tools above.

**👁️ Vision AI Node (Hailo-8)**
- [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)
- [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)
- [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)
- [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)

**🐝 Orchestration & Swarm**
- [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)
- [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)
- [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)
- [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)

**🎮 Digital Twin & Simulation**
- [HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)
- [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)
- [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)
- [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)

**📊 Data & Analytics**
- [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)
- [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)
- [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)
- [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)

**🏭 Industrial Gateway**
- [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)
- [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)
- [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)
- [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)

**🛠️ Complementary Tools**
- [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)
- [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)
- [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)
- [HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)
- [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 AUTHOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE
GPL-3.0 - See LICENSE for details.
