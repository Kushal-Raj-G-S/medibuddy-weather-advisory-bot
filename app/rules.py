"""Generic condition evaluator.

Knows nothing about weather or about any specific SOP. It walks a condition
tree of all_of / any_of / none_of nodes with {field, op, value} leaves and
reports both the verdict and the evidence behind it.

This is the only place a numeric comparison happens, which is what lets a new
SOP be added to sops.yaml with zero code changes: as long as it reuses an
operator listed in OPS and a field the fetcher returns, it evaluates here.
"""

MISSING = object()

OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "between": lambda a, b: b[0] <= a <= b[1],
}

GROUPS = ("all_of", "any_of", "none_of")


class ConditionError(ValueError):
    pass


def validate_condition(node, path="conditions"):
    """Raise ConditionError on a malformed tree. Used at SOP load time so a
    typo in the policy file surfaces immediately instead of silently never
    matching."""
    if not isinstance(node, dict):
        raise ConditionError(f"{path}: expected a mapping, got {type(node).__name__}")

    group_keys = [k for k in node if k in GROUPS]
    if group_keys:
        if len(node) != 1:
            raise ConditionError(f"{path}: a group node must have exactly one key")
        key = group_keys[0]
        children = node[key]
        if not isinstance(children, list) or not children:
            raise ConditionError(f"{path}.{key}: expected a non-empty list")
        for i, child in enumerate(children):
            validate_condition(child, f"{path}.{key}[{i}]")
        return

    if "field" not in node or "op" not in node or "value" not in node:
        raise ConditionError(f"{path}: leaf needs 'field', 'op' and 'value'")
    if node["op"] not in OPS:
        raise ConditionError(
            f"{path}: unsupported op {node['op']!r}; supported: {sorted(OPS)}"
        )
    if node["op"] == "between":
        v = node["value"]
        if not isinstance(v, (list, tuple)) or len(v) != 2:
            raise ConditionError(f"{path}: 'between' needs a two-item [low, high]")
    if node["op"] in ("in", "not_in") and not isinstance(node["value"], (list, tuple)):
        raise ConditionError(f"{path}: {node['op']!r} needs a list value")


def collect_fields(node, out=None):
    """Every weather field name referenced anywhere in a condition tree."""
    out = set() if out is None else out
    for key in GROUPS:
        if key in node:
            for child in node[key]:
                collect_fields(child, out)
            return out
    if "field" in node:
        out.add(node["field"])
    return out


def evaluate(node, facts):
    """Evaluate a condition tree against a flat {field: value} mapping.

    Returns (matched, evidence). Evidence is a list of leaf results, each
    recording the field, operator, threshold and the actual observed value, so
    an answer can always be traced back to the numbers that triggered it.

    A field the fetcher did not return evaluates False rather than raising: the
    bot must never claim a rule fired on data it does not actually have.
    """
    for key in GROUPS:
        if key in node:
            results = [evaluate(child, facts) for child in node[key]]
            verdicts = [r[0] for r in results]
            evidence = [e for r in results for e in r[1]]
            if key == "all_of":
                return all(verdicts), evidence
            if key == "any_of":
                return any(verdicts), evidence
            return not any(verdicts), evidence

    field = node["field"]
    op = node["op"]
    threshold = node["value"]
    actual = facts.get(field, MISSING)

    if actual is MISSING or actual is None:
        return False, [
            {
                "field": field,
                "op": op,
                "threshold": threshold,
                "actual": None,
                "matched": False,
                "missing": True,
            }
        ]

    try:
        matched = bool(OPS[op](actual, threshold))
    except TypeError:
        matched = False

    return matched, [
        {
            "field": field,
            "op": op,
            "threshold": threshold,
            "actual": actual,
            "matched": matched,
            "missing": False,
        }
    ]
