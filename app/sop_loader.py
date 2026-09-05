"""Loads and validates the policy file.

The loader is the only component that reads sops.yaml, and it re-reads the file
whenever its modification time changes. That is what makes an 11th SOP live-
addable: drop it into the YAML, ask the next question, and it is in play. No
restart, no code edit.

It also derives the controlled vocabulary (activity and audience tags) from the
policy file itself, so a new SOP that introduces a brand new activity tag
becomes recognisable to the interpreter without touching any prompt or Python.
"""

from dataclasses import dataclass, field
from typing import Any

import yaml

from app import config
from app.rules import ConditionError, collect_fields, validate_condition

ANY = "any"


class SOPFileError(ValueError):
    pass


@dataclass(frozen=True)
class SOP:
    id: str
    title: str
    category: str
    severity: str
    severity_rank: int
    order: int
    override: bool
    activities: tuple
    audiences: tuple
    conditions: Any
    qualitative_criteria: str
    cite_fields: tuple
    guidance: str

    @property
    def is_judgment_based(self):
        return self.conditions is None

    def covers_activity(self, activity):
        return ANY in self.activities or (activity or "") in self.activities

    def covers_audience(self, audience):
        return ANY in self.audiences or (audience or "") in self.audiences


@dataclass
class PolicySet:
    sops: list
    severity_order: list
    conflict_resolution: dict
    no_match_response: str
    activities: list = field(default_factory=list)
    audiences: list = field(default_factory=list)

    def by_id(self, sop_id):
        for sop in self.sops:
            if sop.id == sop_id:
                return sop
        return None

    @property
    def ids(self):
        return [s.id for s in self.sops]


_cache = {"mtime": None, "policy": None}


def _require(cond, message):
    if not cond:
        raise SOPFileError(message)


def _parse_sop(raw, index, severity_order):
    _require(isinstance(raw, dict), f"sops[{index}]: expected a mapping")
    for key in ("id", "title", "category", "severity", "guidance", "cite_fields"):
        _require(key in raw, f"sops[{index}]: missing required key {key!r}")

    severity = str(raw["severity"]).strip()
    _require(
        severity in severity_order,
        f"{raw['id']}: severity {severity!r} not in severity_order {severity_order}",
    )

    applies = raw.get("applies_to") or {}
    activities = tuple(applies.get("activities") or [ANY])
    audiences = tuple(applies.get("audiences") or [ANY])

    conditions = raw.get("conditions")
    if conditions is not None:
        try:
            validate_condition(conditions)
        except ConditionError as exc:
            raise SOPFileError(f"{raw['id']}: {exc}") from exc

    qualitative = (raw.get("qualitative_criteria") or "").strip()
    if conditions is None:
        _require(
            qualitative,
            f"{raw['id']}: an SOP without 'conditions' must supply "
            "'qualitative_criteria' so judgment is still policy-driven",
        )

    cite_fields = tuple(raw["cite_fields"] or [])
    _require(cite_fields, f"{raw['id']}: cite_fields must not be empty")

    # Any field a condition tests must also be quotable, otherwise the answer
    # could not show its own evidence.
    if conditions is not None:
        missing = sorted(collect_fields(conditions) - set(cite_fields))
        _require(
            not missing,
            f"{raw['id']}: fields tested in conditions but absent from "
            f"cite_fields: {missing}",
        )

    return SOP(
        id=str(raw["id"]).strip(),
        title=str(raw["title"]).strip(),
        category=str(raw["category"]).strip(),
        severity=severity,
        severity_rank=severity_order.index(severity),
        order=index,
        override=bool(raw.get("override", False)),
        activities=activities,
        audiences=audiences,
        conditions=conditions,
        qualitative_criteria=qualitative,
        cite_fields=cite_fields,
        guidance=" ".join(str(raw["guidance"]).split()),
    )


def parse_policy(data):
    _require(isinstance(data, dict), "policy file: top level must be a mapping")

    severity_order = data.get("severity_order")
    _require(
        isinstance(severity_order, list) and severity_order,
        "policy file: 'severity_order' must be a non-empty list",
    )

    raw_sops = data.get("sops")
    _require(
        isinstance(raw_sops, list) and raw_sops,
        "policy file: 'sops' must be a non-empty list",
    )

    sops = [_parse_sop(raw, i, severity_order) for i, raw in enumerate(raw_sops)]

    seen = set()
    for sop in sops:
        _require(sop.id not in seen, f"duplicate SOP id {sop.id!r}")
        seen.add(sop.id)

    activities = sorted({a for s in sops for a in s.activities} - {ANY})
    audiences = sorted({a for s in sops for a in s.audiences} - {ANY})

    return PolicySet(
        sops=sops,
        severity_order=severity_order,
        conflict_resolution=data.get("conflict_resolution") or {},
        no_match_response=" ".join(
            str(
                data.get("no_match_response")
                or "We don't have written guidance covering that."
            ).split()
        ),
        activities=activities,
        audiences=audiences,
    )


def load_policy(path=None, force=False):
    """Return the current PolicySet, re-reading the file if it changed on disk."""
    path = path or config.SOP_FILE
    try:
        mtime = path.stat().st_mtime
    except OSError as exc:
        raise SOPFileError(f"cannot read policy file {path}: {exc}") from exc

    if not force and _cache["policy"] is not None and _cache["mtime"] == mtime:
        return _cache["policy"]

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    policy = parse_policy(data)
    _cache["mtime"] = mtime
    _cache["policy"] = policy
    return policy
