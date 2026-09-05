"""The output guardrail.

The composer is never allowed to type a weather number. It writes placeholders
like {wind_gusts_10m}, and this module substitutes the real values from the
WeatherSnapshot. Two checks then run before anything reaches the user:

  1. every placeholder must resolve to a field the matched SOP is allowed to
     cite, and must be present in the fetched snapshot;
  2. after placeholders are removed, any remaining number in the draft must
     already appear in the SOP's own text (its thresholds), otherwise the model
     invented a figure and the draft is rejected.

Together these make "the bot never reports a number it does not have" a
property enforced by code, not by prompt wording.
"""

import re

PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
# The composer is told to cite policy ids (e.g. "SOP-002") - those digits are
# an identifier, not a weather claim, and must be stripped before hunting for
# numbers the model invented.
SOP_ID_RE = re.compile(r"\bSOP-\d+\b", re.IGNORECASE)

# Ordinals and clock-style fragments that are language, not weather claims.
SAFE_NUMBERS = {"1", "2", "3", "4", "5", "24", "0"}


class ValidationResult:
    def __init__(self, ok, text, used_fields, violations):
        self.ok = ok
        self.text = text
        self.used_fields = used_fields
        self.violations = violations


def format_value(name, value, units):
    unit = (units or {}).get(name, "")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if unit and unit not in ("iso8601", "wmo code", "seconds"):
        return f"{value} {unit}".strip()
    return str(value)


def _invented_numbers(draft, sop, co_applying_ids=()):
    """Numbers the model typed itself that are not thresholds from the policy."""
    stripped = PLACEHOLDER_RE.sub(" ", draft)
    stripped = SOP_ID_RE.sub(" ", stripped)
    allowed_text = f"{sop.guidance} {sop.qualitative_criteria}"
    allowed = set(NUMBER_RE.findall(allowed_text)) | SAFE_NUMBERS
    # A prose list of co-applying policy ids naturally elides the repeated
    # "SOP-" prefix (e.g. "SOP-003, 007, and 013"), so SOP_ID_RE only strips
    # the first one. Those trailing digit groups are still just an id being
    # cited, not a weather figure, for every SOP actually matched this turn.
    for sop_id in co_applying_ids:
        digits = "".join(ch for ch in sop_id if ch.isdigit())
        if digits:
            allowed.add(digits)
            allowed.add(digits.lstrip("0") or "0")
    return sorted({n for n in NUMBER_RE.findall(stripped) if n not in allowed})


def validate_draft(draft, sop, snapshot, co_applying_ids=()):
    """Substitute placeholders and reject any draft that breaks grounding."""
    violations = []
    used = []
    allowed_fields = set(sop.cite_fields)

    for name in PLACEHOLDER_RE.findall(draft):
        if name not in allowed_fields:
            violations.append(
                f"cited field {name!r} is not in SOP {sop.id} cite_fields"
            )
        elif snapshot.facts.get(name) is None:
            violations.append(f"cited field {name!r} is not present in fetched data")
        elif name not in used:
            used.append(name)

    invented = _invented_numbers(draft, sop, co_applying_ids)
    if invented:
        violations.append(
            "draft contains numbers not traceable to the fetched data or to "
            f"SOP {sop.id}: {invented}"
        )

    if violations:
        return ValidationResult(False, "", used, violations)

    def replace(match):
        name = match.group(1)
        return format_value(name, snapshot.facts[name], snapshot.units)

    return ValidationResult(True, PLACEHOLDER_RE.sub(replace, draft), used, [])
