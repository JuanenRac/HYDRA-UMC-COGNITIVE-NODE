# Changelog: HYDRA-UMC-COGNITIVE-NODE 🧠

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `bump_version.py`.

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
