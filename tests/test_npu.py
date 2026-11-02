# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - tests/test_npu.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The budget of the accelerator, with threads that stand in for the services (there is no Hailo-10 here): priority, limits, deadlines and the routes."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from hydra_umc_cognitive_node.api import CognitiveNodeServer
from hydra_umc_cognitive_node.llm import LlmBusy, LlmConfig, Narrator, make_backend
from hydra_umc_cognitive_node.npu import NpuBusy, NpuConfig, NpuConfigError, NpuRequestError, NpuScheduler, load_npu_config, parse_npu_config


def _scheduler(slots: int = 1, **consumers) -> NpuScheduler:
    return NpuScheduler(parse_npu_config({"enabled": True, "slots": slots, **({"consumers": consumers} if consumers else {})}))


def test_it_is_off_by_default():
    assert NpuConfig().enabled is False
    assert parse_npu_config({}).enabled is False
    assert set(parse_npu_config({}).consumers) == {"vla", "stt", "llm"}


@pytest.mark.parametrize("bad", [
    [], {"enabled": "x"}, {"slots": 0}, {"slots": 9}, {"unknown": 1}, {"consumers": {}}, {"consumers": {"a b": {}}}, {"consumers": {"a": {"priority": -1}}},
    {"consumers": {"a": {"other": 1}}}, {"consumers": {"a": {"maxWaitSeconds": 999}}}, {"consumers": {"a": {"maxConcurrent": 0}}},
])
def test_a_bad_configuration_is_refused(bad):
    with pytest.raises(NpuConfigError):
        parse_npu_config(bad)


def test_a_configuration_file_is_read(tmp_path):
    path = tmp_path / "n.json"
    path.write_text(json.dumps({"enabled": True, "slots": 2}), encoding="utf-8")
    assert load_npu_config(str(path)).slots == 2
    with pytest.raises(NpuConfigError):
        load_npu_config(str(tmp_path / "missing.json"))


def test_a_free_device_is_leased_and_given_back():
    scheduler = _scheduler()
    with scheduler.lease("llm") as lease:
        assert scheduler.stats()["held"] == 1 and isinstance(lease, str)
    assert scheduler.stats()["held"] == 0
    assert scheduler.release("nope") is False


def test_an_unknown_consumer_is_refused():
    with pytest.raises(NpuRequestError):
        _scheduler().acquire("camera")


def test_a_busy_device_answers_busy_after_the_wait_of_the_consumer():
    scheduler = _scheduler(llm={"maxWaitSeconds": 0.05})
    first = scheduler.acquire("llm")
    started = time.monotonic()
    with pytest.raises(NpuBusy):
        scheduler.acquire("llm")
    assert time.monotonic() - started < 2
    assert scheduler.stats()["consumers"]["llm"]["busy"] == 1
    scheduler.release(first)


def test_a_caller_can_only_shorten_the_wait():
    scheduler = _scheduler(llm={"maxWaitSeconds": 0.05})
    scheduler.acquire("llm")
    started = time.monotonic()
    with pytest.raises(NpuBusy):
        scheduler.acquire("llm", wait_seconds=60)
    assert time.monotonic() - started < 2


def test_the_higher_priority_waiter_goes_first():
    scheduler = _scheduler(low={"priority": 1, "maxWaitSeconds": 5}, high={"priority": 9, "maxWaitSeconds": 5})
    held = scheduler.acquire("low")
    order: list[str] = []

    def want(name: str) -> None:
        lease = scheduler.acquire(name)
        order.append(name)
        scheduler.release(lease)

    # low has a lease already and maxConcurrent 1, so a second low request waits behind it, and the high one arrives later
    low = threading.Thread(target=want, args=("low",))
    low.start()
    time.sleep(0.1)
    high = threading.Thread(target=want, args=("high",))
    high.start()
    time.sleep(0.1)
    scheduler.release(held)
    low.join(5)
    high.join(5)
    assert order == ["high", "low"]


def test_a_consumer_at_its_limit_does_not_block_the_others():
    scheduler = _scheduler(slots=2, a={"priority": 9, "maxConcurrent": 1, "maxWaitSeconds": 5}, b={"priority": 1, "maxWaitSeconds": 5})
    first = scheduler.acquire("a")
    got: list[str] = []
    waiting_a = threading.Thread(target=lambda: got.append("a" if scheduler.acquire("a") else ""))
    waiting_a.start()
    time.sleep(0.1)
    second = scheduler.acquire("b")  # a is waiting with a higher priority, but it cannot run: b takes the free slot
    scheduler.release(second)
    scheduler.release(first)
    waiting_a.join(5)
    assert got == ["a"]


def test_a_lease_that_is_not_given_back_expires():
    now = [0.0]
    scheduler = NpuScheduler(parse_npu_config({"enabled": True, "consumers": {"llm": {"maxHoldSeconds": 10, "maxWaitSeconds": 1}}}), clock=lambda: now[0])
    scheduler.acquire("llm")
    now[0] = 11.0
    assert scheduler.stats()["held"] == 0 and scheduler.stats()["expiredLeases"] == 1
    scheduler.acquire("llm")


def test_the_language_model_uses_the_budget():
    scheduler = _scheduler(llm={"maxWaitSeconds": 0.05})
    config = LlmConfig(enabled=True, max_concurrent=2)
    narrator = Narrator(config, make_backend(config), scheduler)
    facts = {"sourceId": "m", "kind": "v", "field": "rms", "count": 3, "min": 1, "max": 2, "average": 1.5, "latest": 2, "direction": "up"}
    assert narrator.narrate(facts)["backend"] == "simulator"
    assert scheduler.stats()["consumers"]["llm"]["granted"] == 1
    held = scheduler.acquire("llm")
    with pytest.raises(LlmBusy):
        narrator.narrate(facts)
    scheduler.release(held)


@contextmanager
def _server(scheduler: NpuScheduler | None, token: str = "") -> Iterator[str]:
    server = CognitiveNodeServer(("127.0.0.1", 0), Path("."), Path("."), None, token, scheduler=scheduler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _call(url: str, body: object | None = None, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})}
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode("utf-8"), method="GET" if body is None else "POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_the_routes_do_not_exist_while_it_is_off():
    with _server(None) as base:
        assert _call(base + "/npu/acquire", {"consumer": "llm"})[0] == 404
        assert _call(base + "/npu/release", {"lease": "x"})[0] == 404
        assert _call(base + "/npu")[0] == 404


def test_the_services_lease_over_http():
    scheduler = _scheduler(llm={"maxWaitSeconds": 0.05})
    with _server(scheduler) as base:
        status, answer = _call(base + "/npu/acquire", {"consumer": "llm"})
        assert status == 200
        assert _call(base + "/npu/acquire", {"consumer": "llm"})[0] == 503
        assert _call(base + "/npu")[1]["held"] == 1
        assert _call(base + "/npu/release", {"lease": answer["lease"]}) == (200, {"released": True})
        assert _call(base + "/npu/acquire", {"consumer": "camera"})[0] == 400
        assert _call(base + "/npu/acquire", {"consumer": "llm", "waitSeconds": True})[0] == 400
        assert _call(base + "/npu/release", {"lease": 5})[0] == 400


def test_the_token_is_needed_when_the_node_has_one():
    with _server(_scheduler(), token="t" * 20) as base:
        assert _call(base + "/npu/acquire", {"consumer": "llm"})[0] == 401
        assert _call(base + "/npu")[0] == 401
        assert _call(base + "/npu/acquire", {"consumer": "llm"}, token="t" * 20)[0] == 200
