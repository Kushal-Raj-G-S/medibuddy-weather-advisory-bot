# Weather-Advisory Support Bot

A LangGraph chat agent that answers outdoor-activity safety questions from live
Open-Meteo data, where **every answer is either traceable to a written policy
(SOP) or an explicit refusal**. The model interprets language and phrases the
reply; it never decides what good advice is and never sources a number.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
```

Put your key in `.env` (it is gitignored):

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5
```

`LLM_PROVIDER=openai` with `OPENAI_API_KEY` works identically. Open-Meteo needs
no key.

## Run the chat frontend

```bash
streamlit run frontend/streamlit_app.py
```

Type a question in the thread. Under each reply, expand **Source** to see the
SOP that produced it and the exact fetched values it was allowed to quote, and
**Decision trace** to see what every node decided, including which SOPs were
evaluated and rejected.

## Run the backend without the UI

```bash
python -c "from app.graph import ask; import json; print(json.dumps(ask('is it safe to cycle in Bhopal today?'), indent=2, default=str))"
```

## Run the evals

```bash
pytest evals -v                 # everything (needs API key + network)
pytest evals -v -m offline      # policy/guardrail layer: no key, no network
pytest evals -v -m model        # full graph with weather stubbed (key only)
pytest evals -v -m "live"       # real Open-Meteo + real model
```

The three markers exist because the layers fail for different reasons:
`offline` proves the rules engine, conflict resolution and output guardrail and
is deterministic forever; `model` proves the graph's routing and refusal paths
with weather injected; `live` is the only layer whose result depends on today's
weather, and it skips loudly rather than passing vacuously when conditions are
calm. See `docs/DESIGN.md` §11.

## Layout

```
sops/sops.yaml            the policy set - data, the only source of advice
app/sop_loader.py         loads/validates policy, derives vocabulary, hot-reloads
app/rules.py              generic condition evaluator (no rule-specific code)
app/weather.py            Open-Meteo geocoding + forecast; the only fact source
app/nodes.py              graph nodes
app/graph.py              LangGraph wiring and branching
app/validation.py         output guardrail: placeholder substitution + checks
frontend/streamlit_app.py minimal chat UI with citation panel
evals/test_evals.py       eval suite, three layers
docs/DESIGN.md            every design decision and why
research/                 background research gathered before building
```

## The SOPs, and why YAML

`sops/sops.yaml` holds 13 SOPs across 5 categories
(`situational_override`, `outdoor_exercise`, `travel_commute`,
`vulnerable_groups`, `leisure_social`) spanning all five severities from
`informational` to `critical`, including one deliberately non-numeric
judgment-based SOP (`SOP-012`, leisure outings).

**Why YAML:** a policy owner who is not an engineer has to be able to edit this
during a review call. YAML lets each rule carry inline comments explaining its
own thresholds, and the human-readable `guidance` blocks stay readable at
multi-line length without escaping. The cost is whitespace sensitivity, which
the loader mitigates by validating structure on load and failing loudly with the
offending SOP id rather than silently never matching.

## Adding an 11th SOP without touching code

Append a block to `sops/sops.yaml` and ask the next question. No restart, no
code change. The loader re-reads on file mtime change, and it derives the
activity/audience vocabulary, the severity ranking and the citable-field
allowlist from the file itself — so a new SOP that introduces an activity tag
nobody has used before immediately becomes something the interpreter can select.

```yaml
  - id: SOP-014
    title: Poor air quality during outdoor exertion
    category: outdoor_exercise
    severity: moderate
    applies_to:
      activities: [running, cycling, walking]
      audiences: [any]
    conditions:
      all_of:
        - {field: visibility, op: "<=", value: 4000}
    cite_fields: [visibility, resolved_location]
    guidance: >
      Advise shortening or relocating the session while visibility is at or
      below 4000 m, since haze at this level often accompanies particulate
      loading. Recommend an indoor alternative for anyone with asthma.
```

The one honest caveat: a genuinely new *kind* of comparison (say geospatial
distance, or a time-of-day window as a first-class operator) would need a new
operator in `app/rules.py`. Adding rules needs no code; inventing a new
primitive does. See `docs/DESIGN.md` for the full statement of this limit.

## Design summary

See [docs/DESIGN.md](docs/DESIGN.md) for the reasoning behind the graph shape,
the deterministic-versus-model boundary, conflict resolution, the number-blind
composer, and the known gaps.
