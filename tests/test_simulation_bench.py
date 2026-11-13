# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_simulation_bench.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Simulation bench: the real hub against a simulated family and a simulated accelerator.

The children of the family are small HTTP stand-ins that answer the way a healthy, a sick, a closed, a slow, a garbled and an oversized service do; the hub
probes them with its real probe. The language model is the simulated backend, driven by facts drawn from a fixed seed, and a backend that fails or hangs
stands in for an accelerator that is lost or busy. Nothing here says how a real accelerator or a real language model behaves: that needs the hardware."""
from __future__ import annotations

import json
import random
import re
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from hydra_umc_cognitive_node.family import EXPECTED_CHILDREN
from hydra_umc_cognitive_node.llm import LANGUAGES, LlmBusy, LlmConfig, LlmUnavailable, Narrator, SimulatedBackend
from hydra_umc_cognitive_node.probe import CHILD_URLS_ENV, MAX_ANSWER_BYTES, probe_family

SEED = 20260101


class _Child(BaseHTTPRequestHandler):
    server: "ChildStandIn"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass

    def do_GET(self) -> None:  # noqa: N802
        mode = self.server.mode
        if mode == "closed-health" and self.path == "/health":
            self.send_response(404)
            self.end_headers()
            return
        if mode == "sick":
            self._send(503, b'{"healthy": false}')
        elif mode == "garbled":
            self._send(200, b"<html>not json</html>")
        elif mode == "oversized":
            self._send(200, b'{"ok": true, "pad": "' + b"x" * (MAX_ANSWER_BYTES * 2) + b'"}')
        elif mode == "slow":
            time.sleep(1.0)
            self._send(200, b'{"ok": true}')
        elif mode == "status-word":
            self._send(200, b'{"status": "Ready"}')
        else:
            self._send(200, b'{"healthy": true}')

    def _send(self, code: int, body: bytes) -> None:
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            pass


class ChildStandIn(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, mode: str) -> None:
        super().__init__(("127.0.0.1", 0), _Child)
        self.mode = mode


@contextmanager
def _children(modes: dict[str, str]) -> Iterator[dict[str, str]]:
    servers = {name: ChildStandIn(mode) for name, mode in modes.items()}
    for server in servers.values():
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield {name: f"http://127.0.0.1:{server.server_address[1]}" for name, server in servers.items()}
    finally:
        for server in servers.values():
            server.shutdown()
            server.server_close()


def _env(urls: dict[str, str]) -> dict[str, str]:
    return {CHILD_URLS_ENV: ",".join(f"{name}={url}" for name, url in urls.items())}


def _probe(modes: dict[str, str], tmp_path: Path) -> dict[str, object]:
    with _children(modes) as urls:
        return {item.name: item for item in probe_family(tmp_path, _env(urls))}


def test_a_family_in_every_state_is_told_apart(tmp_path: Path) -> None:
    vla, voice, planner, docs = EXPECTED_CHILDREN
    health = _probe({vla: "healthy", voice: "sick", planner: "garbled", docs: "status-word"}, tmp_path)
    assert health[vla].reachable and health[vla].healthy is True and health[vla].http_status == 200
    assert health[voice].reachable and health[voice].healthy is False and health[voice].http_status == 503 and health[voice].error == "HTTP 503"
    assert health[planner].reachable and health[planner].healthy is True  # an answer that says nothing is "up" when the status is a success
    assert health[docs].healthy is True  # the word "Ready" is a verdict


def test_a_child_that_is_not_there_is_unreachable_and_does_not_hide_the_others(tmp_path: Path) -> None:
    vla, voice, planner, docs = EXPECTED_CHILDREN
    with _children({vla: "healthy"}) as urls:
        urls[voice] = "http://127.0.0.1:9"  # nothing listens on the discard port of a test machine
        urls[planner] = "http://127.0.0.1:9"
        urls[docs] = "http://127.0.0.1:9"
        health = {item.name: item for item in probe_family(tmp_path, _env(urls))}
    assert health[vla].healthy is True
    for name in (voice, planner, docs):
        assert health[name].reachable is False and health[name].healthy is None and health[name].error


def test_a_closed_uniform_route_falls_back_to_stats(tmp_path: Path) -> None:
    vla = EXPECTED_CHILDREN[0]
    manifest = tmp_path / vla
    manifest.mkdir()
    (manifest / "hydra-umc.project.json").write_text(json.dumps({"service": {"health_path": "/health"}}), encoding="utf-8")
    with _children({vla: "closed-health", **{n: "healthy" for n in EXPECTED_CHILDREN[1:]}}) as urls:
        health = {item.name: item for item in probe_family(tmp_path, _env(urls))}
    assert health[vla].url.endswith("/stats") and health[vla].healthy is True


def test_an_oversized_answer_is_read_only_up_to_the_limit(tmp_path: Path) -> None:
    vla = EXPECTED_CHILDREN[0]
    health = _probe({name: ("oversized" if name == vla else "healthy") for name in EXPECTED_CHILDREN}, tmp_path)
    assert health[vla].reachable is True and health[vla].http_status == 200
    # the cut answer is no longer valid JSON, so the child has no verdict of its own and a success status stands
    assert health[vla].healthy is True


def test_a_slow_child_does_not_make_the_probe_fail_when_the_timeout_allows_it(tmp_path: Path) -> None:
    vla = EXPECTED_CHILDREN[0]
    started = time.monotonic()
    health = _probe({name: ("slow" if name == vla else "healthy") for name in EXPECTED_CHILDREN}, tmp_path)
    assert health[vla].healthy is True and (health[vla].latency_ms or 0) >= 900
    assert time.monotonic() - started < 10


def test_a_child_that_is_slower_than_the_timeout_is_unreachable_not_hung(tmp_path: Path) -> None:
    from hydra_umc_cognitive_node.probe import probe_child

    with _children({"HYDRA-UMC-VLA-ENGINE": "slow"}) as urls:
        result = probe_child("HYDRA-UMC-VLA-ENGINE", urls["HYDRA-UMC-VLA-ENGINE"], "/stats", timeout=0.2)
    assert result.reachable is False and result.healthy is None


# ----------------------------------------------------------------------------------------------------------------------- the narrator
def _facts(rng: random.Random, language: str) -> dict:
    low = round(rng.uniform(-5, 5), 2)
    high = round(low + rng.uniform(0.1, 10), 2)
    average = round(rng.uniform(low, high), 2)
    return {"sourceId": f"motor-{rng.randint(1, 9)}", "kind": "vibration", "field": "rms", "count": rng.randint(1, 5000), "min": low, "max": high,
            "average": average, "latest": round(rng.uniform(low, high), 2), "direction": rng.choice(["up", "down", "flat"]), "language": language}


def _narrator(backend=None, **over) -> Narrator:
    config = LlmConfig(enabled=True, **over)
    return Narrator(config, backend or SimulatedBackend(config.simulator_variant))


def test_the_narrative_of_every_language_repeats_only_the_numbers_it_was_given() -> None:
    rng = random.Random(SEED)
    narrator = _narrator()
    for language in LANGUAGES:
        for _ in range(5):
            facts = _facts(rng, language)
            answer = narrator.narrate(facts)
            numbers = {f"{abs(facts[k]):.2f}" for k in ("min", "max", "average", "latest")} | {str(facts["count"])}
            text = answer["narrative"].replace(f'{facts["sourceId"]}/{facts["kind"]}/{facts["field"]}', "")  # the name of the series has digits of its own
            found = set(re.findall(r"\d+(?:\.\d+)?", text))
            assert found <= numbers, (language, found - numbers)
            assert answer["language"] == language and answer["backend"] == "simulator"


def test_the_same_seed_gives_the_same_narratives() -> None:
    def run(seed: int) -> list[str]:
        rng = random.Random(seed)
        narrator = _narrator()
        return [narrator.narrate(_facts(rng, language))["narrative"] for language in LANGUAGES]

    assert run(SEED) == run(SEED) and run(SEED) != run(SEED + 1)


class _Lost:
    name, model = "lost", "none"

    def generate(self, prompt: str, max_tokens: int) -> str:
        raise LlmUnavailable("the accelerator is lost")


class _Blocking:
    name, model = "blocking", "none"

    def __init__(self) -> None:
        self.entered, self.release = threading.Event(), threading.Event()

    def generate(self, prompt: str, max_tokens: int) -> str:
        self.entered.set()
        self.release.wait(5)
        return "Done."


def test_a_lost_accelerator_fails_closed_and_the_next_request_is_not_stuck() -> None:
    narrator = _narrator(_Lost())
    rng = random.Random(SEED)
    for _ in range(3):
        with pytest.raises(LlmUnavailable):
            narrator.narrate(_facts(rng, "en"))
    # the slot was given back each time: a healthy backend now answers at once
    narrator.backend = SimulatedBackend()
    assert narrator.narrate(_facts(rng, "es"))["backend"] == "simulator"


def test_a_second_request_while_the_accelerator_is_busy_is_refused_and_the_first_still_finishes() -> None:
    backend = _Blocking()
    narrator = _narrator(backend, max_concurrent=1)
    rng = random.Random(SEED)
    result: dict[str, object] = {}
    thread = threading.Thread(target=lambda: result.update(narrator.narrate(_facts(rng, "en"))))
    thread.start()
    assert backend.entered.wait(5)
    with pytest.raises(LlmBusy):
        narrator.narrate(_facts(random.Random(SEED + 1), "en"))
    backend.release.set()
    thread.join(5)
    assert result["narrative"] == "Done."
    assert narrator.narrate(_facts(random.Random(SEED + 2), "en"))["narrative"] == "Done."


def test_text_with_control_characters_from_a_model_is_cleaned_before_it_leaves() -> None:
    class Dirty:
        name, model = "dirty", "none"

        def generate(self, prompt: str, max_tokens: int) -> str:
            return "Level\x07 is‮ normal\x00."

    assert _narrator(Dirty()).narrate(_facts(random.Random(SEED), "en"))["narrative"] == "Level is normal."


def test_a_model_that_says_nothing_is_unavailable_not_an_empty_answer() -> None:
    class Mute:
        name, model = "mute", "none"

        def generate(self, prompt: str, max_tokens: int) -> str:
            return "\x07\x00  "

    with pytest.raises(LlmUnavailable):
        _narrator(Mute()).narrate(_facts(random.Random(SEED), "en"))
