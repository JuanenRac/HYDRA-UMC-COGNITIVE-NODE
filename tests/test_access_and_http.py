# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_access_and_http.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The optional bearer token, the limit on simultaneous requests and the shared HTTP module."""
from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from hydra_umc_cognitive_node import http_common
from hydra_umc_cognitive_node.access import bind_warning, is_loopback, load_token
from hydra_umc_cognitive_node.api import CognitiveNodeServer
from hydra_umc_cognitive_node.main import main

TOKEN = "s" * 20


def _get(url: str, token: str = "") -> tuple[int, dict | str]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read().decode()
            return response.status, json.loads(body) if response.headers.get("Content-Type", "").startswith("application/json") else body
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def _serve(tmp_path: Path, **kwargs: object) -> Iterator[tuple[str, CognitiveNodeServer]]:
    server = CognitiveNodeServer(("127.0.0.1", 0), tmp_path, tmp_path, None, **kwargs)  # type: ignore[arg-type]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", server
    server.shutdown()
    server.server_close()


def test_without_a_token_everything_answers_as_before(tmp_path: Path) -> None:
    for base, _ in _serve(tmp_path):
        assert _get(base + "/stats")[0] == 200
        assert _get(base + "/family-status")[0] == 200
        assert _get(base + "/metrics")[0] == 200


def test_with_a_token_every_route_but_the_health_path_needs_it(tmp_path: Path) -> None:
    for base, _ in _serve(tmp_path, token=TOKEN):
        assert _get(base + "/stats")[0] == 200  # the health path stays open for the container health check
        for path in ("/family-status", "/family-status?probe=1", "/metrics", "/nowhere"):
            assert _get(base + path)[0] == 401, path
            assert _get(base + path, "wrong-token-of-16-chars")[0] == 401, path
        assert _get(base + "/family-status", TOKEN)[0] == 200
        assert _get(base + "/metrics", TOKEN)[0] == 200
        assert _get(base + "/nowhere", TOKEN)[0] == 404


def test_a_repeated_query_name_is_still_refused(tmp_path: Path) -> None:
    for base, _ in _serve(tmp_path):
        status, answer = _get(base + "/family-status?probe=1&probe=0")
        assert status == 400 and "exactly once" in str(answer)


def test_the_server_limits_the_requests_it_handles_at_the_same_time(tmp_path: Path) -> None:
    for base, server in _serve(tmp_path, max_threads=1):
        port = int(base.rsplit(":", 1)[1])
        holder = socket.create_connection(("127.0.0.1", port), timeout=5)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=5) as second:
                second.sendall(b"GET /stats HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
                reply = second.recv(4096)
            assert reply.startswith(b"HTTP/1.1 503") and server.refused == 1
        finally:
            holder.close()
    with pytest.raises(ValueError):
        CognitiveNodeServer(("127.0.0.1", 0), tmp_path, tmp_path, None, "", 0)


def test_the_token_comes_from_a_file_or_the_environment_and_must_be_long_enough(tmp_path: Path) -> None:
    assert load_token(None, {}) == ""
    assert load_token(None, {"HYDRA_UMC_COGNITIVE_NODE_TOKEN": TOKEN}) == TOKEN
    (tmp_path / "t").write_text(TOKEN + "\n", encoding="utf-8")
    assert load_token(tmp_path / "t", {"HYDRA_UMC_COGNITIVE_NODE_TOKEN": "x" * 30}) == TOKEN  # the file wins
    (tmp_path / "short").write_text("short", encoding="utf-8")
    with pytest.raises(ValueError, match="at least 16"):
        load_token(tmp_path / "short", {})
    with pytest.raises(ValueError, match="cannot read"):
        load_token(tmp_path / "missing", {})


def test_binding_to_the_network_without_a_token_is_reported_and_not_refused() -> None:
    assert bind_warning("127.0.0.1", "") is None and bind_warning("localhost", "") is None and bind_warning("::1", "") is None
    assert bind_warning("0.0.0.0", TOKEN) is None
    assert "no token" in str(bind_warning("0.0.0.0", ""))  # the container image binds 0.0.0.0 on purpose
    assert is_loopback("[::1]") and not is_loopback("192.168.0.5") and not is_loopback("host.example")


def test_the_serve_command_refuses_a_bad_token_file(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    (tmp_path / "short").write_text("short", encoding="utf-8")
    assert main(["serve", "--port", "0", "--workspace", str(tmp_path), "--token-file", str(tmp_path / "short")]) == 2
    assert "at least 16" in capsys.readouterr().err
    assert main(["serve", "--port", "0", "--workspace", str(tmp_path), "--max-threads", "0"]) == 2
    assert "max_threads" in capsys.readouterr().err


def test_the_copy_of_the_shared_module_is_the_canonical_one() -> None:
    canonical = Path(__file__).resolve().parents[2] / "HYDRA-UMC-SDK" / "tools" / "canonical" / "http_common.py"
    if not canonical.is_file():
        pytest.skip("the SDK checkout is not next to this repository")
    assert Path(http_common.__file__).read_bytes().replace(b"\r\n", b"\n") == canonical.read_bytes().replace(b"\r\n", b"\n")


# ---- the identity of HYDRA-UMC-SERVER (off by default; see server_identity.py)
IDENTITY_KEY = b"a-signing-key-of-the-server-0123456789"


def _signed_token(role: str = "operator", key: bytes = IDENTITY_KEY, exp_offset: int = 600) -> str:
    import base64
    import hashlib
    import hmac
    import time

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps({"username": "ana", "role": role, "exp": int(time.time()) + exp_offset}).encode())
    return f"{head}.{body}.{b64(hmac.new(key, f'{head}.{body}'.encode(), hashlib.sha256).digest())}"


def test_the_identity_of_the_server_is_off_by_default(tmp_path: Path) -> None:
    assert CognitiveNodeServer.identity_key is None
    for base, _ in _serve(tmp_path):
        assert _get(base + "/family-status")[0] == 200
        assert _get(base + "/family-status", _signed_token())[0] == 200  # nothing is asked while it is off
    for base, _ in _serve(tmp_path, token=TOKEN):
        assert _get(base + "/family-status", _signed_token())[0] == 401  # a token of the SERVER means nothing while it is off


def test_with_the_identity_on_a_token_of_the_server_is_accepted_and_nothing_is_open(tmp_path: Path) -> None:
    for base, server in _serve(tmp_path):
        server.identity_key = IDENTITY_KEY
        assert _get(base + "/family-status")[0] == 401  # no credential, even on loopback and without a token of the service
        assert _get(base + "/metrics")[0] == 401
        assert _get(base + "/family-status", "not-a-token")[0] == 401
        assert _get(base + "/family-status", _signed_token("viewer"))[0] == 200
        assert _get(base + "/family-status", _signed_token(key=b"another-key-of-more-than-32-characters!"))[0] == 401
        assert _get(base + "/family-status", _signed_token(exp_offset=-5))[0] == 401
    for base, server in _serve(tmp_path, token=TOKEN):
        server.identity_key = IDENTITY_KEY
        assert _get(base + "/family-status", TOKEN)[0] == 200  # the own token keeps working
        assert _get(base + "/family-status", _signed_token("admin"))[0] == 200


def test_with_the_identity_on_not_even_the_health_path_is_open(tmp_path: Path) -> None:
    for base, server in _serve(tmp_path):
        assert _get(base + "/stats")[0] == 200  # open while the identity is off
        server.identity_key = IDENTITY_KEY
        assert _get(base + "/stats")[0] == 401
        assert _get(base + "/stats", _signed_token("viewer"))[0] == 200
