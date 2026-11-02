# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/npu.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A budget of the accelerator, off by default: one place that hands the Hailo-10 out to the VLA engine, the speech-to-text and the language model.

Each service asks for a lease before it opens the device and gives it back when it is done. A lease has a deadline, so a service that dies cannot keep the
device. When the device is busy the requests wait in a queue ordered by the priority of the consumer (then first come, first served), each one for at most
its own ``maxWaitSeconds``; past it the answer is "busy", never a wait without end. A consumer can also be limited to a number of leases at the same time.

This module does not touch a device. It only decides who may. The language model of this node uses it when it is switched on; the other services reach it
over HTTP (``POST /npu/acquire`` and ``POST /npu/release``). Until there is a Hailo-10 to run on, it is exercised with threads that stand in for the services.
"""
from __future__ import annotations

import json
import re
import secrets
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
DEFAULT_CONSUMERS = {
    "vla": {"priority": 3, "maxWaitSeconds": 2.0, "maxHoldSeconds": 10.0, "maxConcurrent": 1},
    "stt": {"priority": 2, "maxWaitSeconds": 5.0, "maxHoldSeconds": 30.0, "maxConcurrent": 1},
    "llm": {"priority": 1, "maxWaitSeconds": 5.0, "maxHoldSeconds": 60.0, "maxConcurrent": 1},
}


class NpuConfigError(ValueError):
    """The configuration cannot be used; the message says which key and why."""


class NpuRequestError(ValueError):
    """The request is not a well formed lease request."""


class NpuBusy(RuntimeError):
    """The device did not become free inside the time the consumer may wait."""


@dataclass(frozen=True)
class Consumer:
    name: str
    priority: int
    max_wait: float
    max_hold: float
    max_concurrent: int


@dataclass(frozen=True)
class NpuConfig:
    enabled: bool = False
    slots: int = 1
    consumers: dict[str, Consumer] = field(default_factory=dict)


def _consumer(name: str, raw: object) -> Consumer:
    if not _IDENTIFIER.match(name):
        raise NpuConfigError(f"consumer {name[:40]!r} is not an identifier of letters, digits and _ - . :")
    if not isinstance(raw, dict) or set(raw) - {"priority", "maxWaitSeconds", "maxHoldSeconds", "maxConcurrent"}:
        raise NpuConfigError(f"consumer {name}: an object with priority, maxWaitSeconds, maxHoldSeconds and maxConcurrent")

    def number(key: str, default: float, low: float, high: float) -> float:
        value = raw.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise NpuConfigError(f"consumer {name}: {key} must be a number from {low:g} to {high:g}")
        return float(value)

    base = DEFAULT_CONSUMERS.get(name, {"priority": 1, "maxWaitSeconds": 5.0, "maxHoldSeconds": 30.0, "maxConcurrent": 1})
    return Consumer(name, int(number("priority", base["priority"], 0, 100)), number("maxWaitSeconds", base["maxWaitSeconds"], 0, 120),
                    number("maxHoldSeconds", base["maxHoldSeconds"], 1, 3600), int(number("maxConcurrent", base["maxConcurrent"], 1, 16)))


def parse_npu_config(raw: object) -> NpuConfig:
    if not isinstance(raw, dict):
        raise NpuConfigError("the configuration must be a JSON object")
    unknown = set(raw) - {"enabled", "slots", "consumers"}
    if unknown:
        raise NpuConfigError(f"unknown key {sorted(unknown)[0]}")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise NpuConfigError("enabled must be true or false")
    slots = raw.get("slots", 1)
    if isinstance(slots, bool) or not isinstance(slots, int) or not 1 <= slots <= 8:
        raise NpuConfigError("slots must be a whole number from 1 to 8")
    consumers_raw = raw.get("consumers", DEFAULT_CONSUMERS)
    if not isinstance(consumers_raw, dict) or not consumers_raw or len(consumers_raw) > 32:
        raise NpuConfigError("consumers must be an object with 1 to 32 entries")
    consumers = {name: _consumer(name, value) for name, value in consumers_raw.items()}
    return NpuConfig(enabled, slots, consumers)


def load_npu_config(path: str) -> NpuConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NpuConfigError(f"cannot read {path}: {error}") from error
    return parse_npu_config(raw)


@dataclass
class _Lease:
    lease_id: str
    consumer: str
    deadline: float


@dataclass
class _Ticket:
    consumer: str
    priority: int
    order: int


class NpuScheduler:
    def __init__(self, config: NpuConfig, clock: Callable[[], float] = time.monotonic) -> None:
        self.config = config
        self._clock = clock
        self._cond = threading.Condition()
        self._leases: dict[str, _Lease] = {}
        self._waiting: list[_Ticket] = []
        self._order = 0
        self._granted: dict[str, int] = {name: 0 for name in config.consumers}
        self._busy: dict[str, int] = {name: 0 for name in config.consumers}
        self._expired = 0

    def _reap(self) -> None:
        now = self._clock()
        for lease_id in [i for i, lease in self._leases.items() if lease.deadline <= now]:
            del self._leases[lease_id]
            self._expired += 1

    def _held_by(self, consumer: str) -> int:
        return sum(1 for lease in self._leases.values() if lease.consumer == consumer)

    def _may_run(self, ticket: _Ticket) -> bool:
        if len(self._leases) >= self.config.slots:
            return False
        for other in sorted(self._waiting, key=lambda t: (-t.priority, t.order)):
            if self._held_by(other.consumer) >= self.config.consumers[other.consumer].max_concurrent:
                continue  # it cannot run now, so it does not block the others
            return other is ticket
        return False

    def acquire(self, consumer: str, wait_seconds: float | None = None) -> str:
        """A lease id, or ``NpuBusy`` when the device did not become free in time. ``wait_seconds`` can only shorten the wait of the consumer."""
        spec = self.config.consumers.get(consumer)
        if spec is None:
            raise NpuRequestError(f"unknown consumer {consumer[:40]!r}")
        limit = spec.max_wait if wait_seconds is None else max(0.0, min(wait_seconds, spec.max_wait))
        give_up = self._clock() + limit
        with self._cond:
            self._order += 1
            ticket = _Ticket(consumer, spec.priority, self._order)
            self._waiting.append(ticket)
            try:
                while True:
                    self._reap()
                    if self._held_by(consumer) < spec.max_concurrent and self._may_run(ticket):
                        lease = _Lease(secrets.token_hex(16), consumer, self._clock() + spec.max_hold)
                        self._leases[lease.lease_id] = lease
                        self._granted[consumer] += 1
                        return lease.lease_id
                    remaining = give_up - self._clock()
                    if remaining <= 0:
                        self._busy[consumer] += 1
                        raise NpuBusy(f"the accelerator did not become free for {consumer} in {limit:g} s")
                    next_expiry = min((lease.deadline for lease in self._leases.values()), default=give_up)
                    self._cond.wait(timeout=max(0.005, min(remaining, next_expiry - self._clock())))
            finally:
                self._waiting.remove(ticket)
                self._cond.notify_all()

    def release(self, lease_id: str) -> bool:
        with self._cond:
            found = self._leases.pop(lease_id, None) is not None
            self._cond.notify_all()
            return found

    @contextmanager
    def lease(self, consumer: str, wait_seconds: float | None = None) -> Iterator[str]:
        lease_id = self.acquire(consumer, wait_seconds)
        try:
            yield lease_id
        finally:
            self.release(lease_id)

    def stats(self) -> dict[str, Any]:
        with self._cond:
            self._reap()
            return {"slots": self.config.slots, "held": len(self._leases), "waiting": len(self._waiting), "expiredLeases": self._expired,
                    "consumers": {name: {"priority": c.priority, "held": self._held_by(name), "granted": self._granted[name], "busy": self._busy[name]}
                                  for name, c in self.config.consumers.items()}}
