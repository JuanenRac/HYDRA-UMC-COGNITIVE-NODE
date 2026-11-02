# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/llm.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A local language model behind `POST /narrative`, off by default.

The node does not take free text from anyone. A request carries the numbers of a trend summary (count, minimum, maximum, average, latest,
direction) and the identifiers of the series; the node builds the prompt itself from those facts and hands it to a backend. The reply is
cleaned (length, control characters) and returned. Whether the numbers in the text are the numbers that were sent is checked by the caller
(the dashboard verifies every number it is about to show), so a wrong model costs a fallback, never a wrong figure on a screen.

Backends:

  * ``simulator``: a deterministic stand-in that answers from the facts inside the prompt, in the eight languages of the ecosystem. It is
    how everything is developed and tested without a Hailo accelerator. Its ``variant`` can be ``faithful`` (default), ``altered`` (changes
    one number, to prove that the caller's check rejects it) or ``silent`` (answers nothing useful).
  * ``hailo``: the Hailo-10 through HailoRT. It is written against the documented GenAI interface but has NEVER run on a real accelerator:
    any failure (runtime missing, model missing, an exception from the device) is reported as "unavailable" and nothing is guessed.

Everything tuned lives in the JSON file given with ``--llm-config``; without it, or with ``"enabled": false``, the route does not exist.
"""
from __future__ import annotations

import json
import math
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .npu import NpuBusy, NpuScheduler

LANGUAGES = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
DIRECTIONS = ("up", "down", "flat")
MAX_NARRATIVE_CHARS = 2000
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
# the same refusals as the dashboard applies to a narrative: C0 and C1 controls and the bidirectional overrides
_UNSAFE = re.compile("[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f‪-‮⁦-⁩]")


class LlmConfigError(ValueError):
    """The configuration cannot be used; the message says which key and why."""


class LlmRequestError(ValueError):
    """The request is not a well formed set of facts."""


class LlmUnavailable(RuntimeError):
    """The backend cannot answer now (no runtime, no model, a failure of the device, a timeout)."""


class LlmBusy(RuntimeError):
    """Too many narratives are being made at the same time."""


@dataclass(frozen=True)
class LlmConfig:
    enabled: bool = False
    backend: str = "simulator"
    model_path: str | None = None
    max_tokens: int = 160
    max_concurrent: int = 1
    simulator_variant: str = "faithful"


def parse_llm_config(raw: object) -> LlmConfig:
    if not isinstance(raw, dict):
        raise LlmConfigError("the configuration must be a JSON object")
    unknown = set(raw) - {"enabled", "backend", "modelPath", "maxTokens", "maxConcurrent", "simulator"}
    if unknown:
        raise LlmConfigError(f"unknown key {sorted(unknown)[0]}")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise LlmConfigError("enabled must be true or false")
    backend = raw.get("backend", "simulator")
    if backend not in ("simulator", "hailo"):
        raise LlmConfigError('backend must be "simulator" or "hailo"')
    model_path = raw.get("modelPath")
    if model_path is not None and (not isinstance(model_path, str) or not model_path):
        raise LlmConfigError("modelPath must be the path of a file")
    if enabled and backend == "hailo" and model_path is None:
        raise LlmConfigError('backend "hailo" needs modelPath (the compiled model file)')

    def whole(key: str, default: int, low: int, high: int) -> int:
        value = raw.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise LlmConfigError(f"{key} must be a whole number from {low} to {high}")
        return value

    simulator = raw.get("simulator", {})
    if not isinstance(simulator, dict) or set(simulator) - {"variant"}:
        raise LlmConfigError('simulator must be an object with only "variant"')
    variant = simulator.get("variant", "faithful")
    if variant not in ("faithful", "altered", "silent"):
        raise LlmConfigError('simulator.variant must be "faithful", "altered" or "silent"')
    return LlmConfig(enabled, backend, model_path, whole("maxTokens", 160, 16, 1024), whole("maxConcurrent", 1, 1, 16), variant)


def load_llm_config(path: str) -> LlmConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LlmConfigError(f"cannot read {path}: {error}") from error
    return parse_llm_config(raw)


# ------------------------------------------------------------------------------------------------------------------ the facts
@dataclass(frozen=True)
class Facts:
    source_id: str
    kind: str
    field_name: str
    count: int
    minimum: float
    maximum: float
    average: float
    latest: float
    direction: str
    language: str


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise LlmRequestError(f'"{name}" must be a finite number')
    return float(value)


def parse_facts(body: object) -> Facts:
    if not isinstance(body, dict):
        raise LlmRequestError("the body must be a JSON object")
    unknown = set(body) - {"sourceId", "kind", "field", "count", "min", "max", "average", "latest", "direction", "language"}
    if unknown:
        raise LlmRequestError(f"unknown field {sorted(unknown)[0]}")
    ids = []
    for name in ("sourceId", "kind", "field"):
        value = body.get(name)
        if not isinstance(value, str) or not _IDENTIFIER.match(value):
            raise LlmRequestError(f'"{name}" must be 1 to 128 characters of letters, digits, "_", "-", "." or ":"')
        ids.append(value)
    count = body.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise LlmRequestError('"count" must be a whole number of at least 1')
    direction = body.get("direction")
    if direction not in DIRECTIONS:
        raise LlmRequestError('"direction" must be "up", "down" or "flat"')
    language = body.get("language", "en")
    if language not in LANGUAGES:
        raise LlmRequestError(f'"language" must be one of {", ".join(LANGUAGES)}')
    return Facts(ids[0], ids[1], ids[2], count, _finite(body.get("min"), "min"), _finite(body.get("max"), "max"),
                 _finite(body.get("average"), "average"), _finite(body.get("latest"), "latest"), direction, language)


_LANGUAGE_NAMES = {"en": "English", "es": "Spanish", "de": "German", "fr": "French", "it": "Italian", "ja": "Japanese", "zh": "Chinese", "pt": "European Portuguese"}


def build_prompt(facts: Facts) -> str:
    """The prompt is made here from the facts, never from text a client sent."""
    data = {"series": f"{facts.source_id}/{facts.kind}/{facts.field_name}", "samples": facts.count, "min": facts.minimum, "max": facts.maximum,
            "average": facts.average, "latest": facts.latest, "direction": facts.direction}
    return (
        "You write one short factual sentence or two about a measured series for a machine operator. "
        "Use only the numbers in FACTS, copied exactly or rounded, and invent none. No advice, no causes.\n"
        f"LANGUAGE: {facts.language} ({_LANGUAGE_NAMES[facts.language]})\n"
        f"FACTS: {json.dumps(data, sort_keys=True)}\n"
        "ANSWER:"
    )


# ------------------------------------------------------------------------------------------------------------------ the backends
class Backend(Protocol):
    name: str
    model: str

    def generate(self, prompt: str, max_tokens: int) -> str: ...


_DIRECTION_WORDS = {
    "en": {"up": "rising", "down": "falling", "flat": "flat"},
    "es": {"up": "al alza", "down": "a la baja", "flat": "estable"},
    "de": {"up": "steigend", "down": "fallend", "flat": "gleichbleibend"},
    "fr": {"up": "à la hausse", "down": "à la baisse", "flat": "stable"},
    "it": {"up": "in aumento", "down": "in calo", "flat": "stabile"},
    "ja": {"up": "上昇", "down": "下降", "flat": "横ばい"},
    "zh": {"up": "上升", "down": "下降", "flat": "平稳"},
    "pt": {"up": "a subir", "down": "a descer", "flat": "estável"},
}
_TEMPLATES = {
    "en": "{series}: {n} samples between {lo} and {hi}, average {avg}, latest {last}; the trend is {trend}.",
    "es": "{series}: {n} muestras entre {lo} y {hi}, media {avg}, última {last}; la tendencia es {trend}.",
    "de": "{series}: {n} Messwerte zwischen {lo} und {hi}, Mittelwert {avg}, letzter {last}; der Trend ist {trend}.",
    "fr": "{series} : {n} échantillons entre {lo} et {hi}, moyenne {avg}, dernier {last} ; la tendance est {trend}.",
    "it": "{series}: {n} campioni tra {lo} e {hi}, media {avg}, ultimo {last}; l'andamento è {trend}.",
    "ja": "{series}：{n}件のサンプル、{lo}から{hi}、平均{avg}、最新{last}、傾向は{trend}です。",
    "zh": "{series}：{n}个样本，介于{lo}和{hi}之间，平均{avg}，最新{last}，趋势为{trend}。",
    "pt": "{series}: {n} amostras entre {lo} e {hi}, média {avg}, última {last}; a tendência é {trend}.",
}
_SILENT = {"en": "Nothing to report.", "es": "Nada que informar.", "de": "Nichts zu berichten.", "fr": "Rien à signaler.",
           "it": "Niente da segnalare.", "ja": "報告事項はありません。", "zh": "无需报告。", "pt": "Nada a reportar."}


class SimulatedBackend:
    """Answers from the FACTS line of the prompt. Deterministic; no model, no device."""

    name = "simulator"

    def __init__(self, variant: str = "faithful") -> None:
        self.variant = variant
        self.model = f"simulator-{variant}"

    def generate(self, prompt: str, max_tokens: int) -> str:
        language_line = next((l for l in prompt.splitlines() if l.startswith("LANGUAGE: ")), "LANGUAGE: en")
        facts_line = next((l for l in prompt.splitlines() if l.startswith("FACTS: ")), None)
        if facts_line is None:
            raise LlmUnavailable("the prompt carries no facts")
        language = language_line.split()[1]
        language = language if language in LANGUAGES else "en"
        facts = json.loads(facts_line[len("FACTS: "):])
        if self.variant == "silent":
            return _SILENT[language]
        latest = facts["latest"] * 1.37 + 1 if self.variant == "altered" else facts["latest"]
        return _TEMPLATES[language].format(
            series=facts["series"], n=facts["samples"], lo=f"{facts['min']:.2f}", hi=f"{facts['max']:.2f}", avg=f"{facts['average']:.2f}",
            last=f"{latest:.2f}", trend=_DIRECTION_WORDS[language][facts["direction"]])


class HailoBackend:
    """Hailo-10 through HailoRT GenAI. UNTESTED ON HARDWARE: it fails closed, with ``LlmUnavailable``, whatever goes wrong."""

    name = "hailo"

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.model = Path(model_path).name
        self._llm: Any = None
        self._vdevice: Any = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        if self._llm is not None:
            return self._llm
        if not Path(self.model_path).is_file():
            raise LlmUnavailable("the model file of the accelerator is not on this machine")
        try:
            from hailo_platform import VDevice  # type: ignore[import-not-found]
            from hailo_platform.genai import LLM  # type: ignore[import-not-found]
        except ImportError as error:
            raise LlmUnavailable("the HailoRT runtime with GenAI is not installed on this machine") from error
        try:
            self._vdevice = VDevice()
            self._llm = LLM(self._vdevice, self.model_path)
        except Exception as error:  # the device is not there, busy or refuses the model
            raise LlmUnavailable(f"the accelerator could not load the model: {error}") from error
        return self._llm

    def generate(self, prompt: str, max_tokens: int) -> str:
        with self._lock:  # one request at a time on the device
            llm = self._load()
            try:
                return str(llm.generate_all(prompt=prompt, max_generated_tokens=max_tokens))
            except Exception as error:
                raise LlmUnavailable(f"the accelerator failed: {error}") from error


def make_backend(config: LlmConfig) -> Backend:
    if config.backend == "hailo":
        return HailoBackend(config.model_path or "")
    return SimulatedBackend(config.simulator_variant)


def clean_narrative(text: str) -> str:
    text = _UNSAFE.sub("", text).strip()
    if not text:
        raise LlmUnavailable("the model returned no text")
    return text[:MAX_NARRATIVE_CHARS]


@dataclass
class Narrator:
    config: LlmConfig
    backend: Backend
    scheduler: NpuScheduler | None = None  # the budget of the accelerator (npu.py), when it is switched on
    _slots: threading.BoundedSemaphore = field(init=False)

    def __post_init__(self) -> None:
        self._slots = threading.BoundedSemaphore(self.config.max_concurrent)

    def narrate(self, body: object) -> dict[str, str]:
        facts = parse_facts(body)
        if not self._slots.acquire(blocking=False):
            raise LlmBusy("another narrative is being made")
        try:
            if self.scheduler is None:
                text = clean_narrative(self.backend.generate(build_prompt(facts), self.config.max_tokens))
            else:
                try:
                    with self.scheduler.lease("llm"):
                        text = clean_narrative(self.backend.generate(build_prompt(facts), self.config.max_tokens))
                except NpuBusy as error:
                    raise LlmBusy(str(error)) from error
        finally:
            self._slots.release()
        return {"narrative": text, "backend": self.backend.name, "model": self.backend.model, "language": facts.language}
