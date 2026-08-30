# Changelog: HYDRA-UMC-COGNITIVE-NODE 🧠

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `bump_version.py`.

## [Unreleased]

- **Conservative shared-model readiness:** `family-status` no longer treats
  any file or directory under `models/` as runnable weights. It reports
  `present` only for a non-empty local candidate artifact with a recognised
  Hailo/LLM weight extension, ignores symlinks, and continues to make no
  physical-runtime compatibility claim.
- **Documented evidence boundary:** `docs/CLI_REFERENCE.md` now defines the
  exact readiness criterion and distinguishes local inventory evidence from
  Hailo-10 validation on real hardware.

## [0.0.6] - Versioned family-status schema, resource-limited manifest reads, shared-model degradation

- **A real, versioned JSON schema for `family-status`** (`family.py`'s `family_status_to_dict()`, `FAMILY_STATUS_SCHEMA_VERSION`) - the one real input/output contract this integration hub has today. New `family-status --json` prints it directly; the existing human-readable table is unchanged. Every field is real data the check already computed - `schema_version`, `shared_models.{present,path}`, one entry per child (`name`/`present`/`version`/`maturity`/`role`), `all_children_present`.
- **A real resource limit on sibling manifest reads** (`manifest.py`'s `MAX_MANIFEST_BYTES`, 64 KiB) - a corrupted or malicious sibling checkout whose `hydra-umc.project.json` has been replaced by an oversized file now degrades to "not found", the same as any other malformed manifest, instead of being read unbounded into memory.
- **Real degradation-awareness when this node's own shared model weights are missing** (`models.py`, new) - `docker-compose.yml` already documents that this repo owns the quantized LLM/VLA weights (`models/`) shared by its four children; `check_shared_models()` is a real, honest check of that real (currently empty, unprovisioned-on-this-machine) directory. `family-status` now always reports `Shared model weights: present`/`MISSING` in its text output and `shared_models` in its JSON output, so a caller can tell "children are checked out" apart from "children can actually run a model" without inventing a fake ready state.
- 11 new tests (`test_models.py` new, plus additions to `test_manifest.py`/`test_family.py`/`test_cli.py`) = 23 total, including the real oversized-manifest rejection, the real schema-shape assertions for both the all-present and some-missing cases, and both CLI output modes.
- Real verification beyond the test suite: ran `family-status`/`family-status --json` against the actual local ecosystem checkout - correctly reported all 4 real children present with their real, independently-verified version/maturity, and honestly reported this machine's real, empty `models/` directory as missing.

## [0.0.5] - Real v0 family-readiness check
### Added
- `manifest.py` - a real, minimal, defensive reader for a sibling repo's own `hydra-umc.project.json` (name/version/maturity/role), returning `None` for every real failure mode (missing checkout, missing file, malformed JSON, missing field) rather than raising.
- `family.py` - `check_family_status()`: a real check of this node's four real children (`HYDRA-UMC-VLA-ENGINE`/`HYDRA-UMC-VOICE-UI`/`HYDRA-UMC-SEMANTIC-PLANNER`/`HYDRA-UMC-DOCS-QA`) against a real local workspace, reading each one's own manifest rather than a second hand-maintained list.
- `main.py` - new `family-status [--workspace PATH]` subcommand, defaulting to this repo's own parent directory (the real sibling-checkout layout this whole ecosystem already uses). Bare invocation is unchanged: identity/version/role.
- 12 new real tests (`tests/`) - manifest reading for every real failure mode, family-status coverage for all-present/some-missing/none-present, and a real end-to-end CLI round-trip.
- Real verification beyond the test suite: ran `family-status` against the actual local ecosystem checkout on this machine - correctly reported `HYDRA-UMC-VLA-ENGINE` as still `scaffolding` and the other three real siblings as `functional`, matching their real, independently-verified state.

## [0.0.4]
### Added
- Copyright/license header on every source file and build/run script.
- `CHANGELOG.md` (this file).
- Extended documentation across `README.md` and its 4 translations:
  advanced technical/architecture section, detailed build/run
  troubleshooting, and a full "Related Projects" section.

### Changed
- Inline comments explaining the *why* behind non-obvious decisions
  (versioning scheme, src-layout, `docker-compose.yml` wiring).

## [0.0.0]
### Added
- Initial Python scaffolding: `pyproject.toml` (setuptools, src-layout),
  `src/hydra_umc_cognitive_node/__init__.py` + `main.py` (real entry
  point - prints identity/version/role, exits 0).
- `bump_version.py` - odometer-style version bump applied to
  `pyproject.toml` and mirrored into `__init__.py`.
- `build.sh` / `build.bat` - create/activate a venv, install the package
  editable, verify it compiles and imports.
- `run.sh` / `run.bat` - run the entry point.
- `docker-compose.yml` - integration map wiring this node (the parent)
  to its four children (VLA-Engine, Voice-UI, Semantic-Planner, Docs-QA)
  as sibling services on the same Hailo-10 + CM5 hardware, including
  `/dev/hailo0` passthrough and the shared `models/`/`os/` mounts.
