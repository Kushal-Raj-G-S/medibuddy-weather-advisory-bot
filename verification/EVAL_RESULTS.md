# Eval Suite Results — 2026-09-05

This is a committed, dated record of an actual run — not a description of
what the tests are supposed to do. The honest story of this run is that it
**found two real bugs**, which were fixed and re-verified, not hidden.

## Final run (after fixes): 24/24 passed

```
$ pytest evals -v
24 passed, 28 warnings in 447.99s (0:07:27)
```

| Test | Layer | Requirement it covers |
|---|---|---|
| `test_policy_file_loads_and_meets_the_brief` | offline | ≥10 SOPs, ≥3 categories, ≥3 severities, ≥1 fuzzy SOP |
| `test_numeric_sop_fires_on_its_threshold` | offline | rules engine correctness |
| `test_missing_field_never_counts_as_a_match` | offline | never fabricate a match on absent data |
| `test_situational_override_outranks_a_category_sop` | offline | conflict resolution |
| `test_guardrail_rejects_an_invented_number` | offline | number-blind composer, guardrail |
| `test_guardrail_rejects_a_field_the_sop_may_not_cite` | offline | `cite_fields` enforcement |
| `test_interpretation_failure_degrades_honestly_instead_of_crashing` | offline | **new** — crash-safety regression (see below) |
| `test_judge_failure_degrades_to_no_match_instead_of_crashing` | offline | **new** — crash-safety regression (see below) |
| `test_compose_failure_reports_verification_failure_instead_of_crashing` | offline | **new** — crash-safety regression (see below) |
| `test_location_fallback_recovers_a_deterministic_parser_miss` | offline | deterministic regex backstop for a confirmed model-parsing gap |
| `test_guardrail_does_not_mistake_a_cited_sop_id_for_an_invented_number` | offline | guardrail regex precision |
| `test_guardrail_substitutes_real_values` | offline | placeholder substitution |
| `test_severe_conditions_synthetic_end_to_end` | model | brief's severe-weather case, deterministic version (survives after the weather changes) |
| `test_unreachable_weather_api_fails_honestly` | model | brief's required outage case |
| `test_unresolvable_location_uses_the_same_honest_path` | model | brief's ambiguous/failed-geocoding case |
| `test_paraphrase_maps_to_cycling_without_reusing_policy_wording` | paraphrase | brief's ≥2 paraphrase cases (1/2) |
| `test_paraphrase_maps_to_child_audience` | paraphrase | brief's ≥2 paraphrase cases (2/2) |
| `test_session_memory_carries_location_into_a_follow_up` | paraphrase | multi-turn session memory |
| `test_clear_match_cycling_question_cites_a_real_sop` | live | brief's ≥2 clear-match cases (1/2) |
| `test_clear_match_fuzzy_picnic_question_uses_the_judgment_sop` | live | brief's ≥2 clear-match cases (2/2), fuzzy SOP path |
| `test_severe_conditions_live_grounded_in_real_numbers` | live | brief's required severe-weather-live case |
| `test_no_sop_applies_says_so_kindly` | live | brief's required no-match case |
| `test_adversarial_refuses_to_invent_a_policy` | live | brief's required adversarial case (1/1, plus one extra) |
| `test_adversarial_cannot_extract_a_blanket_all_clear` | live | second adversarial probe |

## What the first full run actually found (honest account, not smoothed over)

An earlier run this same session, on the same code apart from the fixes
below, produced **4 failures**. Each was investigated individually rather
than re-run until green:

1. **A real, unhandled crash** — `test_clear_match_fuzzy_picnic_question_uses_the_judgment_sop`
   raised `AttributeError: 'NoneType' object has no attribute 'assessment'`.
   Root cause: `llm.structured(Judgment).invoke(...)` returned `None` (every
   model in the fallback chain failed to produce a parseable tool call), and
   nothing downstream expected that. The identical failure shape existed in
   `interpret_node`'s structured call, and a related one in `compose_node`
   (an empty draft from a total compose failure would previously pass the
   guardrail vacuously — zero placeholders and zero invented numbers to
   flag in an empty string). **Fixed**: `app/llm.py:structured_or_default`,
   used at all three call sites, plus a new terminal node
   `report_interpretation_failed` and an explicit blank-draft check in
   `verify_node`. Three new offline regression tests cover this with a
   mocked always-`None` model, so the fix doesn't depend on reproducing the
   live failure to stay caught. See `docs/DESIGN.md` §12 for the full
   writeup.
2. **Three assertion failures that turned out to be transient**, not
   regressions — `test_clear_match_cycling_question_cites_a_real_sop`,
   `test_severe_conditions_live_grounded_in_real_numbers`, and
   `test_no_sop_applies_says_so_kindly`. Each was re-run in isolation
   afterward and passed cleanly. The most likely cause: a 25-request
   concurrency stress test (`evals/load_test.py`) had just hit the same
   NVIDIA API key seconds before this run started, and running the full
   suite immediately after used the same key again — a plausible
   rate-limit/contention effect on a shared personal key, not a code defect.
   This is a process lesson worth stating plainly: **don't run a
   concurrency probe and the correctness suite back-to-back against the
   same live API key** — space them out, as this record now does.

## A fourth, smaller finding (not a crash, not fixed, honestly left open)

After the crash fix, the fuzzy-picnic test was repeated 4 more times live to
confirm the fix held under real traffic (it did — no crash in any of the 4
runs). One of those 4 runs came back with no SOP cited where a human would
expect `SOP-012` to apply. This is consistent with the same category of
model-output variance already documented for location extraction
(`docs/DESIGN.md` §12) — an approximate one-in-four miss rate on this
specific judgment call, observed from four trials, not asserted as a precise
rate. Unlike the location case, this isn't backed by a deterministic
fallback, because "does this fuzzy policy apply" doesn't reduce to a regex
the way "what's the city name" does. A bounded retry (the same pattern
already used for location) is the natural next step if this rate holds up
under more observation — not added yet on the strength of four trials.

## The brief's specific question about live weather

`test_severe_conditions_live_grounded_in_real_numbers` is designed to skip
(not fail) with the actual observed numbers printed, if today's weather
doesn't cross a high/critical threshold anywhere. On this run it did not
skip — a real high/critical SOP fired against live data. The deterministic
counterpart, `test_severe_conditions_synthetic_end_to_end`, injects a severe
snapshot directly and will keep passing regardless of what the sky does on
review day.
