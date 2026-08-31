# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/api.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Plain JSON/HTTP surface (stdlib http.server) - same convention as this
family's other api.py files. GET /family-status reaches the exact same
check_family_status()/family_status_to_dict() the CLI's own `family-status
--json` already runs - this module doesn't add a second JSON shape, it
reuses the one main.py's own --json flag already produces."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .family import check_family_status, family_status_to_dict
from .models import check_shared_models


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: object) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _write_error(handler: BaseHTTPRequestHandler, status: int, message: str) -> None:
    _write_json(handler, status, {"error": message})


def _query_params(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    parsed = urlparse(handler.path)
    values = parse_qs(parsed.query, keep_blank_values=True)
    repeated = sorted(key for key, value in values.items() if len(value) != 1)
    if repeated:
        raise ValueError(f"query parameters must occur exactly once: {repeated}")
    return {key: value[0] for key, value in values.items()}


class Handler(BaseHTTPRequestHandler):
    server: "CognitiveNodeServer"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # quiet by default, same reasoning as this family's other api.py files

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            params = _query_params(self)
        except ValueError as error:
            _write_error(self, 400, str(error))
            return

        if path == "/family-status":
            workspace = Path(params["workspace"]) if "workspace" in params else self.server.workspace
            statuses = check_family_status(workspace)
            shared_models = check_shared_models(self.server.repo_root)
            _write_json(self, 200, family_status_to_dict(statuses, shared_models))
        elif path == "/stats":
            _write_json(self, 200, {"workspace": str(self.server.workspace)})
        else:
            _write_error(self, 404, "not found")


class CognitiveNodeServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], workspace: Path, repo_root: Path) -> None:
        super().__init__(address, Handler)
        self.workspace = workspace
        self.repo_root = repo_root
