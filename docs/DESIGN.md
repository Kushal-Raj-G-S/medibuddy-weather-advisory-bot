# Design decisions

Written to be defended line by line. Where something is a genuine gap, it is
stated as one rather than hidden.

## 1. The core problem, restated

Two requirements pull in opposite directions:

- questions arrive as free text, paraphrased, so matching must tolerate language
  the policy file never anticipated;
- no advice and no number may originate from the model, so the model must have
  as little discretion as possible.

The whole design is one answer to that tension: **let the model translate, not
decide.** It converts messy language into a controlled vocabulary, and it
converts a fixed policy into fluent prose. Everything between those two
translations is deterministic Python.

## 2. Where the boundary sits

| Concern | Owner | Why |
| --- | --- | --- |
| Understanding paraphrase, resolving follow-ups | model | Irreducibly a language problem |
| Fetching weather | code | Must be the sole fact source |
| Evaluating numeric conditions | code | Auditable, unit-testable, identical every run |
| Ranking and conflict resolution | code | A policy decision, not a judgment call |
| Judging non-numeric SOPs | model, narrowly | No threshold exists to check |
| Wording the reply | model | Language, with no factual authority |
| Substituting numbers, verifying the draft | code | The guarantee has to be mechanical |

The consequence worth noticing: **paraphrase robustness and policy matching are
decoupled.** The model maps "pedal to the office" onto the `cycling` tag; the
rules engine then matches on the tag. Semantic matching never touches the policy
thresholds, so a fuzzy input cannot produce a fuzzy threshold decision.

## 3. Graph shape

```
START → interpret ─┬→ report_interpretation_failed ─┐
                   ├→ refuse_override ──────────────┤
                   ├→ ask_location ─────────────────┤
                   ├→ report_no_guidance ───────────┤
                   └→ fetch ─┬→ report_unavailable ──┤
                             └→ match ─┬→ report_no_guidance
                                       └→ compose → verify ─┬→ report_verification_failure
                                                            └→ record_turn → END
```

Six terminal paths, five of them refusals. Each branch is a routing function
over graph state, not a `try/except` around a happy path — the graph physically
cannot reach `compose` without a resolved location, a successful fetch and a
matched SOP. `report_interpretation_failed` (added after a real crash was
found and fixed — see §12) is what a total interpretation failure routes to,
distinct from `report_no_guidance`: one means "we hit a technical problem
understanding you," the other means "we understood and have no policy for
it" — conflating them would misrepresent what actually happened.

`record_turn` is the join point: every path, including refusals, records the
turn into message history, so a refusal is still context for the next turn.

## 4. SOP representation

YAML, with a schema that admits two kinds of rule:

- **threshold rules** carry a `conditions` tree (`all_of` / `any_of` / `none_of`
  over `{field, op, value}` leaves). Evaluated entirely in code.
- **judgment rules** omit `conditions` and carry `qualitative_criteria`
  instead. The loader *requires* one or the other, so "fuzzy" can never
  degrade into "unspecified".

Every SOP also declares `cite_fields`, an allowlist of weather fields its answer
may quote. The loader rejects any SOP that tests a field it cannot cite, since
such an answer could not show its own evidence.

Why not embeddings for matching: with 13 rules the retrieval problem does not
exist, and a similarity threshold would become an undocumented policy knob
nobody owns. Why not one big LLM call over all rule text: it would put the
matching decision and the whole rule set inside a single model call, which is
both the widest prompt-injection surface and the hardest thing to unit-test.

## 5. Conflict resolution — decided on purpose

Declared in `sops.yaml` under `conflict_resolution`, so it is itself policy:

1. any SOP with `override: true` leads, regardless of category;
2. otherwise highest severity wins the primary citation;
3. ties break by declaration order in the file (stable and inspectable);
4. **every other matching SOP is always disclosed** by id, title and severity.

Rationale: under-warning is the expensive failure for a safety advisory, so the
most severe rule leads. But silently discarding the others would hide policy
coverage from the user and from an auditor, so they are listed without being
expanded. `SOP-001` and `SOP-002` are the `override` rules.

## 6. The situational SOP (`SOP-001`)

The case the brief cares about most: an organised rain system is not one
threshold. No single reading looks alarming — 1006 hPa is unremarkable, 47 km/h
gusts are survivable, 20 mm of rain is a wet day — but together they indicate a
system rather than a shower.

`SOP-001` therefore tests three fields at once (`pressure_msl <= 1008` **and**
`precipitation_sum >= 15` **and** `wind_gusts_10m_max >= 35`) and carries
`override: true`, so it pre-empts every category rule and leads the answer. The
signal is derived from live fields on every request; no event, date or place is
hardcoded anywhere.

Honest limit: this is a proxy for an IMD bulletin, not the bulletin itself.
Open-Meteo exposes no "well-marked low-pressure area" flag, so the SOP infers
the situation from the physics it can see. A production version should ingest the
IMD district bulletin directly and treat that as an additional fact source; the
schema would not need to change, only a new field would appear in `facts`.

## 7. The fuzzy SOP (`SOP-012`)

"Is today good for a picnic" has no defensible cutoff, so `SOP-012` supplies
*ordered factors to weigh* rather than a threshold, and explicitly forbids
issuing a safety verdict — if a real safety threshold is crossed, another SOP
outranks it anyway under the override/severity rules.

This is how "fuzzy but not free-floating" is kept meaningful: the model's
latitude is confined to weighing factors the policy names, in the order the
policy names them, and its output is a boolean plus a numeral-free assessment.

## 8. The number-blind composer

The strongest guarantee in the system, and the one worth demonstrating live.

The composing model **never receives a weather value.** It gets:

- the SOP's guidance text,
- the list of field *names* it may cite,
- threshold-relative phrases generated in code ("`wind_gusts_10m` is at or above
  its policy threshold"), never the value,
- for judgment SOPs, an assessment string that has had numerals stripped.

It writes `{wind_gusts_10m}` and `app/validation.py` substitutes the real figure
from the snapshot. Two checks then run:

1. every placeholder must be in the SOP's `cite_fields` and present in the
   fetched data;
2. after placeholders are removed, any remaining numeral must appear verbatim in
   the SOP's own text — otherwise the model invented a figure and the draft is
   discarded in favour of the `report_verification_failure` path.

So "the bot never reports a number it does not have" is not a prompt
instruction that usually holds. The model has no number to misreport, and the
verifier rejects the draft if one appears anyway. That is enforced at
`app/validation.py:validate_draft`, called from `app/nodes.py:verify_node`.

## 9. Session memory

`MemorySaver` keyed by `thread_id` persists the whole state, so history survives
across turns and resets on restart, exactly as scoped.

Beyond raw messages, the state carries `session_facts` (`location`, `activity`,
`audience`). The interpreter receives them and fills only what the current
message leaves unsaid, which is what makes "what about this evening instead?"
resolve to the same city and activity with a shifted window. Windows are
resolved deterministically: `app/weather.py` aggregates the hourly series over
the named part of the day (worst gust, total rain, lowest visibility), so the
same SOP condition works for "now" and "this evening" without being rewritten.

## 10. Adversarial case, and why this one

Chosen: **talking the model into citing a policy that does not exist.** The
user's text flows straight into an LLM call, and a fabricated citation is the
failure that most directly breaks the business promise — an answer that looks
policy-backed but is not is worse than a refusal, because it survives review.

It is defended in three independent places, which is the point:

1. the interpreter classifies override attempts and routes to `refuse_override`
   before any policy is consulted;
2. SOP selection is structural, not textual — the matcher only ever returns SOPs
   the loader parsed, so a model cannot name `SOP-999` into existence;
3. the citation shown in the UI is built from the loaded SOP object, so the
   panel cannot display a policy that is not in the file.

Prompt-injection defence that relies only on instructions would satisfy none of
these. `NeMo Guardrails` was considered for this and scoped out: its input/output
rails would duplicate defences 1 and 3, and it would add a second framework's
configuration surface for no additional guarantee within this timebox.

## 11. Eval design, and the live-weather problem

Three layers, because they fail for different reasons:

- **offline** — synthetic facts, no network, no model. Proves the rules engine,
  conflict resolution and guardrail. Deterministic, so it keeps passing forever.
- **paraphrase** — real model call, asserts a controlled-vocabulary *tag*
  rather than prose, so the assertion stays deterministic.
- **live** — real API. Assertions are conditional on what the API returns.

The brief's question about a suite outliving a weather event is answered
directly: `test_severe_conditions_synthetic_end_to_end` injects a severe
snapshot and asserts the full path, so the severe-weather behaviour is proven
without depending on the sky. `test_severe_conditions_live` checks whether any
high/critical threshold is genuinely crossed right now and **skips loudly with
the observed numbers** if not, rather than passing vacuously. A green run on a
calm day therefore reports "not asserted today" instead of false confidence.

## 12. Model selection (nvidia provider)

The brief leaves model choice open and grades how it's constrained, not which
one is picked - so the provider is an env switch (`app/llm.py`) and this
project also supports an NVIDIA NIM endpoint with a fallback chain, verified
empirically rather than by name recognition:

1. Listed all 81 models on the account, then probed a representative subset
   with a simplified 3-field tool call. 7 returned correct structured output;
   the rest 404'd (not enabled on this account), 500'd, or timed out past 90s.
2. Re-tested the 7 survivors against the ACTUAL 7-field `Interpretation`
   schema this project uses, since a simple probe is not the real workload.
   Two regressions surfaced: `nemotron-3.5-lightning-30b-a3b` returns a hard
   400 (`unknown field guided_json`) - it cannot serve the structured-output
   mode LangChain selects for this schema, not a soft degradation. Two more
   (`mistral-nemotron`, `kimi-k3`) timed out completely (40s+, twice each)
   despite passing the simplified probe.
3. Of the two that fully worked (`nemotron-3-ultra-550b-a55b`,
   `gpt-oss-20b`), a further run revealed `nemotron-3-ultra-550b` intermittently
   drops the `location` field (1 miss in 3 identical calls) despite returning a
   structurally valid response - so `with_fallbacks()`, which only reacts to
   exceptions, would not have caught it. `interpret_node` (`app/nodes.py`) adds
   a bounded one-shot retry specifically for this: if a fresh question yields
   an empty location, retry once before trusting the empty result.

Net result: `NVIDIA_MODEL=nvidia/nemotron-3-ultra-550b-a55b`, fallback chain
`openai/gpt-oss-20b` then `nvidia/nemotron-3.5-lightning-30b-a3b` (the last one
still fine for the unstructured `compose` call even though it cannot do
structured output on this account). This is a smaller, less impressive-looking
list than "5 verified models" - the honest finding is that most of the
initially-promising candidates did not survive contact with the real schema,
and shipping a wider fallback chain padded with unverified names would trade a
true guarantee for a longer list.

**A second, sharper finding surfaced once the eval suite ran against live
traffic**: `nemotron-3-ultra-550b` returned an empty `location` on 5/5 identical
calls for "Is it safe to cycle in Bhopal today?" - not a flake, a deterministic
gap for that phrasing. Direct inspection of the raw response (bypassing
LangChain's parsing) showed why: the model *did* write `"location": "Bhopal"`,
but inside malformed JSON in the text content (`[[{ ... }]`, unbalanced
brackets) rather than the API's structured tool-call slot, so the parser
extracted nothing. The model had the right answer and failed to deliver it in
a machine-readable envelope - which means a same-prompt retry cannot fix it
(confirmed: it doesn't), but a cheap, bounded deterministic extractor can. See
`app/nodes.py:_fallback_location` - it fires only when the structured path
already came back empty, so a false positive is no worse than the prior
failure mode (still resolves through `geocode()` / `ask_location`), while a
true positive recovers an answer the model already had.

**A third finding, the most serious of the three**: during a full eval-suite
run, `test_clear_match_fuzzy_picnic_question_uses_the_judgment_sop` crashed
with `AttributeError: 'NoneType' object has no attribute 'assessment'` -
`llm.structured(Judgment).invoke(...)` returned `None` outright (every model
in the fallback chain apparently failing to produce a parseable tool call),
and nothing downstream expected that. The same failure mode existed in
`interpret_node`'s structured call. Both are architecturally significant: an
unhandled crash is a *worse* failure than any of the honest refusal paths,
because it doesn't reach the user as an answer at all - it's a 500, not a
"we don't have guidance for that." Fixed with `llm.structured_or_default()`
(`app/llm.py`), used at both call sites, plus a new dedicated terminal node,
`report_interpretation_failed`, distinct from `report_no_guidance` because
"we hit a technical problem" and "we understood but have no policy" are
different facts and conflating them would misrepresent what happened. The
same crash shape existed in `compose_node` (an empty draft from a total
compose failure would previously pass `validate_draft` vacuously, since an
empty string has zero placeholders and zero invented numbers to flag) -
`verify_node` now checks for a blank draft explicitly before validating.
All three are covered by offline regression tests
(`test_interpretation_failure_degrades_honestly_instead_of_crashing`,
`test_judge_failure_degrades_to_no_match_instead_of_crashing`,
`test_compose_failure_reports_verification_failure_instead_of_crashing`)
using a mocked always-`None` model, so this doesn't depend on reproducing the
live failure to stay caught.

**Repeating the fuzzy-picnic case 4 more times live after the fix** (to check
whether it still crashes - it didn't, in any of the 4) surfaced a fourth,
smaller thing worth being honest about: one of the four runs came back with
no SOP cited when a human would expect SOP-012 to apply. Not a crash, and
consistent with the same category of model-output variance already
documented above for location extraction - an approximate one-in-four miss
rate on this specific judgment call, observed, not asserted precisely (four
trials is not a real sample size). Unlike the location case, this one isn't fed through a
deterministic backstop, because "does this fuzzy policy apply" doesn't reduce
to a regex the way "what's the city name" does - a bounded retry (the same
pattern used for location) is the natural next fix if this rate holds up
under more observation, but is not yet added on the strength of four trials.
Left as a known, stated limitation rather than a fix asserted on thin
evidence.

## 13. A state-leak bug across turns, found via real multi-turn testing

Reproduced live, not hypothesised: asking "is today a good day for a picnic
in Bengaluru?" then, in the same session, a vague follow-up ("so I can do
outing for real") once produced a blank answer *alongside a fully-formed
SOP-012 citation* - severity, category, cited values, all present, next to
no text. That combination is exactly the failure this whole system exists
to prevent (an answer that looks policy-backed but isn't), just
self-inflicted rather than caused by the model.

Root cause: LangGraph's checkpointer persists state across turns for a
`thread_id`, and a node's returned dict only overwrites the keys it
includes - keys it omits keep whatever value the previous turn left there.
`verify_node`'s two failure branches returned `{"answer": ""}` with no
`"citation"` key, so when turn 2's draft failed (a one-off compose hiccup -
re-running the identical two turns afterward succeeded normally, confirming
this is transient, not a permanent break), turn 1's real citation was still
sitting in state and leaked through unchanged.

Fixed: both branches now explicitly set
`"citation": {"sop_id": None, "reason": "failed_output_validation"}`, never
leaving the key unset. Covered by
`test_verify_failure_clears_a_prior_turns_stale_citation`, which plants a
stale citation in state before calling `verify_node` directly, so the test
doesn't depend on reproducing the live timing to stay caught. Every other
node in `app/nodes.py` was audited for the same pattern (grepped for every
`"answer": ""` return) - only these two had it.

## 14. Known gaps

- **New operators need code.** Adding rules is pure data, but a genuinely new
  primitive (geospatial, first-class time-of-day windows) means editing
  `OPS` in `app/rules.py`. Rule addition is code-free; primitive invention is not.
- **Geocoding takes the first result silently.** Ambiguous names resolve to the
  most populous match; alternatives are captured on the snapshot but not yet
  surfaced as a clarifying question. Empty or failed geocoding does route to the
  same honest refusal as an outage.
- **`SOP-001` infers the system, it does not read a bulletin.** See §6.
- **The interpreter is a single model call with no fallback.** If it returns an
  off-vocabulary tag the value is coerced to empty, which can under-match rather
  than mis-match — the safer direction, but it means a badly worded question can
  land on `no_sop_applies` when a rule arguably covered it.
- **`weather_code: max` as "worst".** Higher WMO codes are broadly more severe,
  which holds for the thunderstorm range this policy set tests, but it is an
  ordering assumption rather than a semantic one.
