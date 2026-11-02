# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/access.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The optional bearer token of the HTTP API.

The token is off unless one is given (`--token-file` or the HYDRA_UMC_COGNITIVE_NODE_TOKEN environment variable). With one, every request but the health path
(`GET /stats`, which the container health check and the service registry read and which says nothing about the node) must carry `Authorization: Bearer <token>`;
the comparison takes constant time and is the one of the shared HTTP module. Without one the API answers anyone who can reach it, so binding an address that is
not loopback without a token is reported on the standard error: the container image does it on purpose (its port is published by the compose file), and the
node says so each time instead of staying quiet.
"""
from __future__ import annotations

import ipaddress
import os
from pathlib import Path

TOKEN_ENV = "HYDRA_UMC_COGNITIVE_NODE_TOKEN"
MIN_TOKEN_LENGTH = 16
HEALTH_PATH = "/stats"


def is_loopback(addr: str) -> bool:
    if addr.strip().lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(addr.strip().strip("[]")).is_loopback
    except ValueError:
        return False


def load_token(token_file: str | Path | None, environ: dict[str, str] | None = None) -> str:
    """The configured token ("" when none). Raises ValueError for an unreadable file or a token that is too short."""
    env = os.environ if environ is None else environ
    token = env.get(TOKEN_ENV, "").strip()
    if token_file:
        try:
            token = Path(token_file).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as error:
            raise ValueError(f"cannot read the token file: {error}") from error
    if token and len(token) < MIN_TOKEN_LENGTH:
        raise ValueError(f"the bearer token must have at least {MIN_TOKEN_LENGTH} characters")
    return token


def bind_warning(addr: str, token: str) -> str | None:
    """A sentence when the API is open to the network without a token, None otherwise."""
    if token or is_loopback(addr):
        return None
    return f"--addr {addr} is not loopback and there is no token: anyone who can reach the port can read the state of the family (give --token-file, or {TOKEN_ENV})"
