# Proof: Adding an 11th SOP Without Touching Code

The brief says: *"We'll ask you, live in the review call, to add an 11th SOP
on the spot without touching your control-flow code. Design for that
moment."* This file is that moment, actually performed on 2026-09-05 during
this build, not just described as something the design supports.

## 1. Baseline — before the new SOP exists

```
$ python -c "from app.graph import ask, build_graph; ..."
ask('is it safe to go running in Chennai today given the smog?', ...)

BEFORE SOP-014 exists:
{
  "sop_id": null,
  "reason": "no_sop_applies"
}
```

Correct — no policy covers air quality/visibility for outdoor exercise yet,
and the bot says so rather than guessing.

## 2. The only change made

One block appended to `sops/sops.yaml`. **No file under `app/` was touched.**
The FastAPI server (`uvicorn api.main:app`) that had already been running
throughout this whole session was **not restarted**.

```yaml
  - id: SOP-014
    title: Reduced visibility during outdoor exercise (haze / low air quality)
    category: outdoor_exercise
    severity: moderate
    applies_to:
      activities: [running, cycling, walking, hiking]
      audiences: [any]
    conditions:
      all_of:
        - {field: visibility, op: "<=", value: 4000}
    cite_fields: [visibility, resolved_location]
    guidance: >
      Advise shortening or relocating the session while visibility is at or
      below 4000 m, since haze or particulate loading at this level can
      irritate airways during sustained exertion. Recommend an indoor
      alternative for anyone with asthma or a respiratory condition, and
      recommend a lower-intensity effort if the session goes ahead outdoors.
```

## 3. Confirmed picked up, with zero restart

```
$ python -c "from app.sop_loader import load_policy; ..."
SOP count now: 14
Has SOP-014: True
```

```
$ python -c "from app.rules import evaluate; ..."
Hazy (2500m) matches: True
Clear (20000m) matches: False
```

```
$ curl -s http://localhost:8010/api/policy | ...
count: 14
has SOP-014: True
```

That last check is the important one: it hit the **already-running** FastAPI
process from before this file existed. The loader's mtime check
(`app/sop_loader.py:load_policy`) re-reads the file automatically on the next
request — no restart, no redeploy, no code path outside `sops.yaml` touched.

## 4. Existing test suite unaffected

```
$ pytest evals -v -m offline
9 passed, 15 deselected in 0.89s
```

`test_policy_file_loads_and_meets_the_brief` asserts `>= 10` SOPs, not an
exact count, so it (correctly) doesn't need updating just because the policy
set grew — that's the point of the requirement.
