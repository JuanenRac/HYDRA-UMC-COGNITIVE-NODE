# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/api.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Plain JSON/HTTP surface (stdlib http.server) - same convention as this
family's other api.py files. GET /family-status reaches the exact same
check_family_status()/family_status_to_dict() the CLI's own `family-status
--json` already runs - this module doesn't add a second JSON shape, it
reuses the one main.py's own --json flag already produces."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from . import __version__
from .access import HEALTH_PATH
from .http_common import DEFAULT_MAX_THREADS, SOCKET_TIMEOUT_SECONDS, BoundedThreadingHTTPServer, bearer_matches, query_params, read_json_object, reject_unauthorized, write_error, write_json
from .llm import LlmBusy, LlmRequestError, LlmUnavailable, Narrator
from .service_metrics import MetricsHandlerMixin
from .family import check_family_status, family_status_to_dict
from .probe import health_to_dict, probe_family
from .models import check_shared_models


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: object) -> None:
    write_json(handler, status, payload)


def _write_error(handler: BaseHTTPRequestHandler, status: int, message: str) -> None:
    write_error(handler, status, message)


def _query_params(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    return query_params(handler)  # a name that occurs twice is refused


class Handler(MetricsHandlerMixin, BaseHTTPRequestHandler):
    server: "CognitiveNodeServer"
    metrics_service = "hydra-umc-cognitive-node"
    metrics_version = __version__

    # Seconds a client may stay silent on its connection before the server
    # drops it, so a client that connects and sends nothing cannot hold a
    # handler thread forever. Socket I/O only; never the time a check takes.
    timeout = SOCKET_TIMEOUT_SECONDS

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # quiet by default, same reasoning as this family's other api.py files

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/narrative" or self.server.narrator is None:
            _write_error(self, 404, "not found")  # the route does not exist while the language model is off
            return
        if not bearer_matches(self, self.server.token):
            reject_unauthorized(self)
            return
        try:
            body = read_json_object(self, 8 * 1024)
        except ValueError as error:
            _write_error(self, 400, f"invalid request: {error}")
            return
        try:
            _write_json(self, 200, self.server.narrator.narrate(body))
        except LlmRequestError as error:
            _write_error(self, 400, f"invalid request: {error}")
        except LlmBusy as error:
            self.send_response(503)
            self.send_header("Retry-After", "2")
            payload = ('{"error": "%s"}' % error).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except LlmUnavailable as error:
            _write_error(self, 503, f"the language model is not available: {error}")

    def do_GET(self) -> None:  # noqa: N802
        authorized = bearer_matches(self, self.server.token)
        if self.serve_metrics(authorized=authorized):
            return
        path = urlparse(self.path).path
        # the health path stays open so the container health check and the service registry can read it without the token; everything else needs it when one is set
        if path != HEALTH_PATH and not authorized:
            reject_unauthorized(self)
            return
        try:
            params = _query_params(self)
        except ValueError as error:
            _write_error(self, 400, str(error))
            return

        if path == "/family-status":
            if "workspace" in params:
                # which directory is scanned is decided by whoever starts the
                # service, never by a request (it would be a file-existence oracle)
                _write_error(self, 400, "the workspace is fixed when the service starts")
                return
            statuses = check_family_status(self.server.workspace)
            shared_models = check_shared_models(self.server.repo_root, self.server.models_dir)
            health = None
            if params.get("probe") in ("1", "true"):
                # where the children are is fixed when the node starts (see probe.py); a request only says whether to ask them
                health = {h.name: health_to_dict(h) for h in probe_family(self.server.workspace)}
            _write_json(self, 200, family_status_to_dict(statuses, shared_models, health))
        elif path == "/stats":
            _write_json(self, 200, {"status": "ok"})
        else:
            _write_error(self, 404, "not found")


class CognitiveNodeServer(BoundedThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        workspace: Path,
        repo_root: Path,
        models_dir: Path | None = None,
        token: str = "",
        max_threads: int = DEFAULT_MAX_THREADS,
        narrator: Narrator | None = None,
    ) -> None:
        super().__init__(address, Handler, max_threads)
        # empty means no token (see access.py); with one, every route but the health path needs it
        self.token = token
        self.workspace = workspace
        self.repo_root = repo_root
        self.models_dir = models_dir
        # POST /narrative (llm.py) exists only with a narrator, which main.py builds when the language model is switched on
        self.narrator = narrator
