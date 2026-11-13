# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/remote.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""`family-status` for children that are not checked out: their manifests are read from the published repositories.

Off unless asked for (`family-status --remote`). Only one address shape is ever requested, `https://raw.githubusercontent.com/JuanenRac/<child>/<ref>/hydra-umc.project.json`
with <child> one of the expected children and <ref> a plain branch or tag name, so the option cannot be turned into a request for anything else. The answer is
read up to the same size limit as a local manifest; any failure (no network, a 404, an answer that is too large or not a manifest) degrades to "not found", the same
as a missing checkout. The fetcher is a parameter so the tests never touch the network.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from collections.abc import Callable

from .family import EXPECTED_CHILDREN, ChildStatus
from .manifest import MANIFEST_FILE, MAX_MANIFEST_BYTES, parse_child_manifest

RAW_BASE = "https://raw.githubusercontent.com/JuanenRac"
DEFAULT_REF = "main"
DEFAULT_TIMEOUT_S = 5.0
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")

Fetcher = Callable[[str, float], bytes | None]


def validate_ref(ref: str) -> str:
    """The branch or tag name [ref], or ValueError (slashes, `..` and anything that is not a plain name are refused)."""
    if not isinstance(ref, str) or _REF.fullmatch(ref) is None or ".." in ref:
        raise ValueError(f"not a plain branch or tag name: {ref!r}")
    return ref


def manifest_url(child: str, ref: str = DEFAULT_REF) -> str:
    """The one address a manifest is read from; ValueError for a child that is not expected or a ref that is not plain."""
    if child not in EXPECTED_CHILDREN:
        raise ValueError(f"not an expected child: {child!r}")
    return f"{RAW_BASE}/{child}/{validate_ref(ref)}/{MANIFEST_FILE}"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def fetch_https(url: str, timeout: float) -> bytes | None:
    """The body of [url] up to MAX_MANIFEST_BYTES, or None for any failure or an answer larger than that. Redirects are not followed."""
    if not url.startswith(RAW_BASE + "/"):
        return None
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "hydra-umc-cognitive-node"}), timeout=timeout) as answer:  # noqa: S310
            body = answer.read(MAX_MANIFEST_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return None if len(body) > MAX_MANIFEST_BYTES else body


def check_remote_family_status(ref: str = DEFAULT_REF, fetch: Fetcher | None = None, timeout: float = DEFAULT_TIMEOUT_S) -> list[ChildStatus]:
    """The status of every expected child read from its published manifest at [ref]; the same shape as `check_family_status`."""
    reader = fetch if fetch is not None else fetch_https
    statuses = []
    for child in EXPECTED_CHILDREN:
        body = reader(manifest_url(child, ref), timeout)
        manifest = None
        if body is not None:
            try:
                manifest = parse_child_manifest(body.decode("utf-8"))
            except UnicodeDecodeError:
                manifest = None
        statuses.append(ChildStatus(name=child, present=manifest is not None, manifest=manifest))
    return statuses
