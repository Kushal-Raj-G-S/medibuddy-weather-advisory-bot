# Requirements Checklist — Verified Against the Assignment Brief

Every row below was checked against the actual repo state on 2026-09-05, not
recalled from memory. Where a check involved running something, the command
and its real output are quoted. This file is the answer to "did you build
everything the brief asks for" — see the other files in this folder for the
eval and load-test evidence, and `docs/DESIGN.md` for the reasoning behind
each design decision.

## What you're building

| Requirement | Status | Evidence |
|---|---|---|
| LangGraph agent, real branching (not one prompt-response chain) | ✅ | `app/graph.py` — 5 terminal paths (`compose→verify`, `ask_location`, `report_unavailable`, `report_no_guidance`, `refuse_override`, `report_verification_failure`), each reached by a `add_conditional_edges` routing function over graph state, not a linear chain |
| Pulls live weather data | ✅ | `app/weather.py` calls the real Open-Meteo forecast + geocoding endpoints |
| Finds the SOP that applies, or determines none does | ✅ | `app/nodes.py:match_node` + `report_no_guidance_node` |
| Replies traceable to that SOP | ✅ | every response carries a `citation` object with `sop_id`, or an explicit `reason` when none applies |
| Model choice is yours, API key out of git | ✅ | `LLM_PROVIDER` env switch (anthropic/openai/nvidia) in `app/llm.py`; `.env` is gitignored, confirmed with `git check-ignore -v .env` → matched `.gitignore:1:.env` |
| Session memory, multi-turn, doesn't make user repeat themselves | ✅ | `MemorySaver` keyed by `thread_id` (`app/graph.py`) + `session_facts` carried in state; tested live in `evals/test_evals.py::test_session_memory_carries_location_into_a_follow_up` |
| Chat frontend, minimal, actually runs | ✅ | Next.js app (`web/`) — primary; Streamlit (`frontend/streamlit_app.py`) — fallback, no separate API server needed |

## The policy rules (SOPs)

| Requirement | Status | Evidence |
|---|---|---|
| At least 10 SOPs | ✅ **14** | `load_policy(force=True)` → `len(p.sops) == 14` (13 originally + SOP-014 added live during this verification pass, see `SOP_LIVE_ADD_DEMO.md`) |
| At least 3 categories | ✅ **5** | `situational_override, outdoor_exercise, travel_commute, vulnerable_groups, leisure_social` |
| A range of severities, not everything "dangerous" | ✅ **all 5** | `informational, low, moderate, high, critical` all present |
| At least one fuzzy/non-numeric SOP | ✅ | `SOP-012` (picnic/leisure suitability) has no `conditions` block, only `qualitative_criteria`; the loader (`app/sop_loader.py`) *requires* one or the other, so a rule can't silently be neither |
| Conflict resolution decided on purpose, stated | ✅ | `sops.yaml: conflict_resolution` block + `docs/DESIGN.md` §5 — override SOPs lead, then highest severity, ties by file order, all matches disclosed |

## Non-negotiables

| Requirement | Status | Evidence |
|---|---|---|
| Every answer traceable to a specific SOP, or explicit "no SOP applies" | ✅ | `citation.sop_id` is never null without a `reason`; verified in `test_no_sop_applies_says_so_kindly` |
| Adding/changing a policy needs zero changes to weather/model code | ✅ | Proven live, not just claimed — see `SOP_LIVE_ADD_DEMO.md`: added SOP-014 to `sops.yaml` only, confirmed picked up by the already-running FastAPI server (never restarted) |
| Never answers with a forecast it doesn't have | ✅ | `test_unreachable_weather_api_fails_honestly`, `test_unresolvable_location_uses_the_same_honest_path` — both route to the same honest `weather_unavailable` refusal |
| Never invents generic advice when no policy covers the question | ✅ | `test_no_sop_applies_says_so_kindly` |
| Bot only composes language, doesn't decide facts — numbers must be real | ✅ | The composer is **number-blind by construction**: it writes `{field_name}` placeholders, never a value; `app/validation.py:validate_draft` substitutes real figures and rejects any numeral not traceable to the API response or the SOP's own text. See `docs/DESIGN.md` §8. |
| "We'll ask you to add an 11th SOP on the spot" | ✅ | Actually performed, not just designed for — see `SOP_LIVE_ADD_DEMO.md` |

## Proving it works (eval suite)

| Requirement | Status | Evidence |
|---|---|---|
| ≥2 cases an SOP clearly applies | ✅ (2+) | `test_clear_match_cycling_question_cites_a_real_sop`, `test_clear_match_fuzzy_picnic_question_uses_the_judgment_sop` |
| ≥2 paraphrased cases (not reusing SOP wording) | ✅ (2) | `test_paraphrase_maps_to_cycling_without_reusing_policy_wording` ("pedal to the office"), `test_paraphrase_maps_to_child_audience` ("4-year-old", never says "child") |
| ≥1 genuinely severe live-weather case, grounded in real numbers | ✅ (2 — live + synthetic) | `test_severe_conditions_live_grounded_in_real_numbers` (skips honestly if today is calm) + `test_severe_conditions_synthetic_end_to_end` (deterministic, survives a calm day) |
| ≥1 no-SOP-applies case | ✅ | `test_no_sop_applies_says_so_kindly` |
| ≥1 simulated unreachable weather API | ✅ (2) | `test_unreachable_weather_api_fails_honestly`, `test_unresolvable_location_uses_the_same_honest_path` |
| ≥1 adversarial case, justified | ✅ (2) | `test_adversarial_refuses_to_invent_a_policy` (fabricated `SOP-999`), `test_adversarial_cannot_extract_a_blanket_all_clear` — see `docs/DESIGN.md` §10 for why this specific risk was chosen |
| Each case states what's checked, what pass looks like, whether it passed | ✅ | Every test has a docstring in this shape; `EVAL_RESULTS.md` in this folder is the actual dated run output, committed as a hand-in artifact rather than left only in chat |
| Honest about failures, not a suite guaranteed to pass | ✅ | 3 real bugs were found and documented during this build (see `docs/DESIGN.md` §12 and the git history) rather than hidden; `EVAL_RESULTS.md` reports skips honestly when live weather doesn't cross a threshold |

## What to hand in

| Requirement | Status | Evidence |
|---|---|---|
| Standalone git repo | ✅ | Public: https://github.com/Kushal-Raj-G-S/medibuddy-weather-advisory-bot |
| README with setup + run instructions, backend AND frontend | ✅ | `README.md` — Next.js, Streamlit, and API-only paths all documented |
| SOPs with a one-line note on why that form | ✅ | `README.md` "The SOPs, and why YAML" |
| LangGraph implementation | ✅ | `app/graph.py`, `app/nodes.py`, `app/state.py` |
| Eval suite with results and honest notes on failures | ✅ | `evals/test_evals.py` + `verification/EVAL_RESULTS.md` (this folder) |

## Beyond what's required (flagged so it's not mistaken for scope creep)

- **Two frontends** (Next.js primary, Streamlit fallback) — only one was required.
- **A concurrency/stress probe** (`evals/load_test.py`, results in `LOAD_TEST_RESULTS.md`) — not asked for by the brief, added because it's a fair question about production readiness distinct from correctness.
- **NVIDIA NIM model chain empirically verified** rather than picked by name recognition — see `docs/DESIGN.md` §12; two of the four initially-shortlisted fallback models were dropped after they failed against the real schema.

## Known, stated gaps (not hidden)

See `docs/DESIGN.md` §13 for the full list. Briefly: adding a genuinely new
*kind* of numeric comparison (not just a new rule) needs a small code change
in `app/rules.py`; geocoding ambiguity picks the first result silently rather
than asking the user to disambiguate; `SOP-001` infers an organised weather
system from physics fields rather than reading an actual IMD bulletin.
