# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/__init__.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""HYDRA-UMC-COGNITIVE-NODE - Semantic reasoning & GenAI edge node (Hailo-10).

Parent/integration package for the Cognitive AI Node category of the
HYDRA-UMC ecosystem. Ties together VLA-Engine, Voice-UI, Semantic-Planner
and Docs-QA as the "frontal lobe" that turns voice/text instructions into
robotic mission logic - see docker-compose.yml for how the four children
are wired together on the same Hailo-10 + CM5 hardware.
"""


# Single source of truth for the package version - mirrored into
# pyproject.toml's own `version =` field by bump_version.py on every real
# build, rather than the more common "read version from package metadata
# at import time" approach: this way `main.py` can print a version even
# when the package was never installed (e.g. run straight from src/).
__version__ = "0.0.5"