# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/probe.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Does each child answer? `family-status` reads the manifests, which says what is installed; this asks the running services.

Each child has a port it listens on and a health route its manifest declares (`service.health_path`; `/stats` when it declares none). The
probe makes one GET to that route with a short timeout and reports whether it answered and with what status, how long it took, and what the
child itself says about its health (a JSON `healthy` or `status` field, when the answer has one). It sends no credentials: the health routes
of the children are the open ones.

Where the children are is fixed when the node starts, never by a request: by default each one on the loopback port its systemd unit uses, and
`HYDRA_UMC_COGNITIVE_NODE_CHILD_URLS` (for example `HYDRA-UMC-VOICE-UI=http://voice-ui:8091,...`) says otherwise, as a container needs.
Only `http://` and `https://` addresses are accepted.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .family import EXPECTED_CHILDREN

# The port each child listens on (the same ones docker-compose.yml publishes and the systemd units use).
DEFAULT_CHILD_PORTS: dict[str, int] = {
    "HYDRA-UMC-VLA-ENGINE": 8098,
    "HYDRA-UMC-VOICE-UI": 8091,
    "HYDRA-UMC-SEMANTIC-PLANNER": 8109,
    "HYDRA-UMC-DOCS-QA": 8110,
}
DEFAULT_HEALTH_PATH = "/stats"
CHILD_URLS_ENV = "HYDRA_UMC_COGNITIVE_NODE_CHILD_URLS"
PROBE_TIMEOUT_SECONDS = 2.0
MAX_ANSWER_BYTES = 64 * 1024


def child_base_urls(environ: dict[str, str] | None = None) -> dict[str, str]:
    """The address of every child: the loopback default, replaced by what `HYDRA_UMC_COGNITIVE_NODE_CHILD_URLS` lists."""
    env = os.environ if environ is None else environ
    urls = {name: f"http://127.0.0.1:{port}" for name, port in DEFAULT_CHILD_PORTS.items()}
    raw = env.get(CHILD_URLS_ENV, "").strip()
    if not raw:
        return urls
    for item in raw.split(","):
        name, separator, url = item.strip().partition("=")
        name, url = name.strip(), url.strip().rstrip("/")
        if not separator or name not in EXPECTED_CHILDREN:
            raise ValueError(f"{CHILD_URLS_ENV}: {item.strip()!r} is not NAME=URL for one of {', '.join(EXPECTED_CHILDREN)}")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f"{CHILD_URLS_ENV}: {url!r} must be an http:// or https:// address without credentials")
        urls[name] = url
    return urls


def health_path_of(workspace: Path, child: str) -> str:
    """The health route the manifest of a child declares, or `/stats`."""
    try:
        data = json.loads((workspace / child / "hydra-umc.project.json").read_text(encoding="utf-8"))
        path = data.get("service", {}).get("health_path")
    except (OSError, ValueError, AttributeError):
        return DEFAULT_HEALTH_PATH
    return path if isinstance(path, str) and path.startswith("/") and len(path) < 128 and " " not in path else DEFAULT_HEALTH_PATH


@dataclass(frozen=True)
class ChildHealth:
    name: str
    url: str
    reachable: bool
    http_status: int | None
    latency_ms: int | None
    # what the child says about itself when its answer has a verdict: True / False, or None when it has none
    healthy: bool | None
    error: str | None


def _verdict(body: bytes) -> bool | None:
    try:
        data = json.loads(body)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("healthy"), bool):
        return data["healthy"]
    if isinstance(data.get("ok"), bool):
        return data["ok"]
    status = data.get("status")
    if isinstance(status, str):
        return status.lower() in ("ok", "healthy", "ready", "up")
    return None


def probe_child(name: str, base_url: str, health_path: str, *, timeout: float = PROBE_TIMEOUT_SECONDS, opener=urllib.request.urlopen) -> ChildHealth:
    url = base_url + health_path
    started = time.monotonic()
    try:
        with opener(urllib.request.Request(url, method="GET", headers={"Accept": "application/json"}), timeout=timeout) as response:
            body = response.read(MAX_ANSWER_BYTES)
            status = response.status
    except urllib.error.HTTPError as error:
        # the service answered, with an error status: it is up and says it is not well
        return ChildHealth(name, url, True, error.code, int((time.monotonic() - started) * 1000), False, f"HTTP {error.code}")
    except (urllib.error.URLError, OSError, ValueError) as error:
        return ChildHealth(name, url, False, None, None, None, str(getattr(error, "reason", error))[:200])
    latency = int((time.monotonic() - started) * 1000)
    verdict = _verdict(body)
    return ChildHealth(name, url, True, status, latency, True if verdict is None and 200 <= status < 300 else verdict, None)


def probe_family(workspace: Path, environ: dict[str, str] | None = None, *, opener=urllib.request.urlopen) -> list[ChildHealth]:
    urls = child_base_urls(environ)
    return [probe_child(name, urls[name], health_path_of(workspace, name), opener=opener) for name in EXPECTED_CHILDREN]


def health_to_dict(health: ChildHealth) -> dict:
    return {
        "reachable": health.reachable,
        "http_status": health.http_status,
        "latency_ms": health.latency_ms,
        "healthy": health.healthy,
        "url": health.url,
        "error": health.error,
    }
