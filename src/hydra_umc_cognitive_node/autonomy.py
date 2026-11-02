# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - src/hydra_umc_cognitive_node/autonomy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The autonomy policy: the one place that decides how far an output of the AI services may go, off by default.

A proposal of the VLA engine, an intent of the voice interface or a plan of the semantic planner asks this node for a level and gets back the highest level
the policy grants to that source, and a decision:

  * ``inform``: the output may be shown, never acted upon;
  * ``propose``: the output may become a proposal that a person reviews;
  * ``execute_with_confirmation``: the output may be executed, but only after a person confirmed that very action.

The policy is a JSON file (``--autonomy-config``). A source that is not listed gets ``defaultLevel``, which is ``inform`` unless the file says otherwise, so a new
service can never move hardware before somebody wrote it down. Anything that is not understood is a refusal, never a grant. Every decision is appended to an
audit log chained by SHA-256, so a line that is removed or edited breaks the chain. The log holds identifiers and the decision, never the content of a proposal.

The confirmation flag is what the caller says: the node does not see the person. The route therefore needs the bearer token whenever the node is reachable from
the network, and who may call it is the operator's decision (see docs/AUTONOMY.md).
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LEVELS = ("inform", "propose", "execute_with_confirmation")
LANGUAGES = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
MAX_AUDIT_BYTES_LIMIT = 256 * 1024 * 1024

# reason code -> the sentence in each language (pt is European Portuguese)
REASONS: dict[str, dict[str, str]] = {
    "allowed": {
        "en": "Allowed at the requested level.",
        "es": "Permitido en el nivel pedido.",
        "de": "Auf der angeforderten Stufe erlaubt.",
        "fr": "Autorisé au niveau demandé.",
        "it": "Consentito al livello richiesto.",
        "ja": "要求されたレベルで許可されました。",
        "zh": "已按请求的级别允许。",
        "pt": "Permitido no nível pedido.",
    },
    "level_limited": {
        "en": "The policy grants this source a lower level than the one requested.",
        "es": "La política concede a esta fuente un nivel inferior al pedido.",
        "de": "Die Richtlinie gewährt dieser Quelle eine niedrigere Stufe als angefordert.",
        "fr": "La politique accorde à cette source un niveau inférieur à celui demandé.",
        "it": "La politica concede a questa fonte un livello inferiore a quello richiesto.",
        "ja": "ポリシーはこのソースに、要求より低いレベルしか付与しません。",
        "zh": "策略授予此来源的级别低于所请求的级别。",
        "pt": "A política concede a esta fonte um nível inferior ao pedido.",
    },
    "needs_confirmation": {
        "en": "A person must confirm this exact action before it is executed.",
        "es": "Una persona debe confirmar esta acción exacta antes de ejecutarla.",
        "de": "Eine Person muss genau diese Aktion bestätigen, bevor sie ausgeführt wird.",
        "fr": "Une personne doit confirmer cette action précise avant son exécution.",
        "it": "Una persona deve confermare questa azione esatta prima dell'esecuzione.",
        "ja": "実行する前に、担当者がこの操作を確認する必要があります。",
        "zh": "执行前必须由人员确认这一具体操作。",
        "pt": "Uma pessoa tem de confirmar esta ação exata antes de a executar.",
    },
    "confirmed": {
        "en": "Executed with the confirmation of a person.",
        "es": "Ejecución con la confirmación de una persona.",
        "de": "Ausführung mit Bestätigung einer Person.",
        "fr": "Exécution avec la confirmation d'une personne.",
        "it": "Esecuzione con la conferma di una persona.",
        "ja": "担当者の確認のうえで実行できます。",
        "zh": "经人员确认后可执行。",
        "pt": "Execução com a confirmação de uma pessoa.",
    },
    "unknown_source_inform_only": {
        "en": "This source is not in the policy: it may only inform.",
        "es": "Esta fuente no está en la política: solo puede informar.",
        "de": "Diese Quelle steht nicht in der Richtlinie: sie darf nur informieren.",
        "fr": "Cette source n'est pas dans la politique : elle ne peut qu'informer.",
        "it": "Questa fonte non è nella politica: può solo informare.",
        "ja": "このソースはポリシーに記載がないため、通知のみ可能です。",
        "zh": "此来源不在策略中：只能提供信息。",
        "pt": "Esta fonte não consta da política: só pode informar.",
    },
    "denied": {
        "en": "Not allowed by the policy.",
        "es": "No permitido por la política.",
        "de": "Von der Richtlinie nicht erlaubt.",
        "fr": "Non autorisé par la politique.",
        "it": "Non consentito dalla politica.",
        "ja": "ポリシーにより許可されていません。",
        "zh": "策略不允许。",
        "pt": "Não permitido pela política.",
    },
}


class AutonomyConfigError(ValueError):
    """The policy file cannot be used; the message says which key and why."""


class AutonomyRequestError(ValueError):
    """The request is not a well formed question."""


@dataclass(frozen=True)
class AutonomyConfig:
    enabled: bool = False
    default_level: str = "inform"
    sources: dict[str, str] = field(default_factory=dict)
    audit_file: str | None = None
    audit_max_bytes: int = 10 * 1024 * 1024
    audit_memory: int = 200


def parse_autonomy_config(raw: object) -> AutonomyConfig:
    if not isinstance(raw, dict):
        raise AutonomyConfigError("the configuration must be a JSON object")
    unknown = set(raw) - {"enabled", "defaultLevel", "sources", "auditFile", "auditMaxBytes", "auditMemory"}
    if unknown:
        raise AutonomyConfigError(f"unknown key {sorted(unknown)[0]}")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise AutonomyConfigError("enabled must be true or false")
    default_level = raw.get("defaultLevel", "inform")
    if default_level not in LEVELS:
        raise AutonomyConfigError(f"defaultLevel must be one of {', '.join(LEVELS)}")
    sources_raw = raw.get("sources", {})
    if not isinstance(sources_raw, dict):
        raise AutonomyConfigError("sources must be an object of source -> level")
    if len(sources_raw) > 256:
        raise AutonomyConfigError("sources has more than 256 entries")
    sources: dict[str, str] = {}
    for name, level in sources_raw.items():
        if not _IDENTIFIER.match(name):
            raise AutonomyConfigError(f"source {name[:40]!r} is not an identifier of letters, digits and _ - . :")
        if level not in LEVELS:
            raise AutonomyConfigError(f"source {name}: the level must be one of {', '.join(LEVELS)}")
        sources[name] = level
    audit_file = raw.get("auditFile")
    if audit_file is not None and (not isinstance(audit_file, str) or not audit_file):
        raise AutonomyConfigError("auditFile must be the path of a file")
    sizes = {}
    for key, default, low, high in (("auditMaxBytes", 10 * 1024 * 1024, 4096, MAX_AUDIT_BYTES_LIMIT), ("auditMemory", 200, 1, 5000)):
        value = raw.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise AutonomyConfigError(f"{key} must be a whole number from {low} to {high}")
        sizes[key] = value
    return AutonomyConfig(enabled, default_level, sources, audit_file, sizes["auditMaxBytes"], sizes["auditMemory"])


def load_autonomy_config(path: str) -> AutonomyConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AutonomyConfigError(f"cannot read {path}: {error}") from error
    return parse_autonomy_config(raw)


class AuditLog:
    """Append-only JSONL chained by SHA-256, with a bounded copy in memory. When the file passes its size the next line starts a new file and the
    old one is kept as ``<name>.1`` (one backup); the chain continues across the rotation because the first line of the new file names the last hash."""

    def __init__(self, path: str | None, max_bytes: int, memory: int) -> None:
        self.path = Path(path) if path else None
        self.max_bytes = max_bytes
        self._recent: deque[dict[str, Any]] = deque(maxlen=memory)
        self._lock = threading.Lock()
        self._last = "0" * 64
        if self.path is not None:
            self._last = self._tail_hash()

    def _tail_hash(self) -> str:
        assert self.path is not None
        try:
            with self.path.open("rb") as handle:
                lines = handle.read().splitlines()
        except OSError:
            return "0" * 64
        for line in reversed(lines):
            try:
                return str(json.loads(line)["hash"])
            except (ValueError, KeyError, TypeError):
                continue
        return "0" * 64

    def record(self, entry: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            body = dict(entry, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), prev=self._last)
            digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            line = dict(body, hash=digest)
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.exists() and self.path.stat().st_size >= self.max_bytes:
                    backup = self.path.with_name(self.path.name + ".1")
                    self.path.replace(backup)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n")
            self._last = digest
            self._recent.append(line)
            return line

    def recent(self, limit: int) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._recent)[-limit:][::-1]


def verify_chain(lines: list[str]) -> int:
    """Number of lines of a chained log whose hashes are intact; raises ValueError naming the first broken line."""
    prev = None
    for number, text in enumerate(lines, 1):
        try:
            line = json.loads(text)
            digest = line.pop("hash")
        except (ValueError, KeyError, AttributeError) as error:
            raise ValueError(f"line {number} is not a log line") from error
        if prev is not None and line.get("prev") != prev:
            raise ValueError(f"line {number} does not follow the previous one")
        if hashlib.sha256(json.dumps(line, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest() != digest:
            raise ValueError(f"line {number} was changed")
        prev = digest
    return len(lines)


@dataclass(frozen=True)
class Question:
    source: str
    kind: str
    action_id: str
    level: str
    confirmed: bool
    language: str


def parse_question(body: object) -> Question:
    if not isinstance(body, dict):
        raise AutonomyRequestError("the body must be a JSON object")
    unknown = set(body) - {"source", "kind", "actionId", "level", "humanConfirmed", "language"}
    if unknown:
        raise AutonomyRequestError(f"unknown field {sorted(unknown)[0]}")
    ids = []
    for name in ("source", "kind", "actionId"):
        value = body.get(name)
        if not isinstance(value, str) or not _IDENTIFIER.match(value):
            raise AutonomyRequestError(f'"{name}" must be 1 to 128 characters of letters, digits, "_", "-", "." or ":"')
        ids.append(value)
    level = body.get("level")
    if level not in LEVELS:
        raise AutonomyRequestError(f'"level" must be one of {", ".join(LEVELS)}')
    confirmed = body.get("humanConfirmed", False)
    if not isinstance(confirmed, bool):
        raise AutonomyRequestError('"humanConfirmed" must be true or false')
    language = body.get("language", "en")
    if language not in LANGUAGES:
        raise AutonomyRequestError(f'"language" must be one of {", ".join(LANGUAGES)}')
    return Question(ids[0], ids[1], ids[2], str(level), confirmed, str(language))


class AutonomyPolicy:
    def __init__(self, config: AutonomyConfig) -> None:
        self.config = config
        self.audit = AuditLog(config.audit_file, config.audit_max_bytes, config.audit_memory)

    def granted_level(self, source: str) -> tuple[str, bool]:
        """The level the policy gives a source, and whether the source is in the policy."""
        if source in self.config.sources:
            return self.config.sources[source], True
        return self.config.default_level, False

    def evaluate(self, body: object) -> dict[str, Any]:
        question = parse_question(body)
        granted, known = self.granted_level(question.source)
        requested_rank, granted_rank = LEVELS.index(question.level), LEVELS.index(granted)
        if requested_rank > granted_rank:
            decision, reason = "deny", ("level_limited" if known else "unknown_source_inform_only")
        elif question.level == "execute_with_confirmation":
            decision, reason = ("allow", "confirmed") if question.confirmed else ("needs_confirmation", "needs_confirmation")
        else:
            decision, reason = "allow", "allowed"
        entry = self.audit.record({"source": question.source, "kind": question.kind, "actionId": question.action_id, "requested": question.level,
                                   "granted": granted, "humanConfirmed": question.confirmed, "decision": decision, "reason": reason})
        return {"decision": decision, "reason": reason, "message": REASONS[reason][question.language], "requestedLevel": question.level,
                "grantedLevel": granted, "language": question.language, "auditHash": entry["hash"]}

    def describe(self) -> dict[str, Any]:
        return {"defaultLevel": self.config.default_level, "sources": dict(self.config.sources), "levels": list(LEVELS)}
