# Load / Concurrency Test Results

Run at 2026-09-05T03:08:59+00:00 UTC.

Not required by the assignment brief (which asks for correctness/
grounding/failure-handling evals, covered in `evals/test_evals.py`), but
a fair question about production readiness. Checks 1 and 2 stub the LLM
and weather calls (deterministic, free, no rate limits) so they isolate
*this codebase's* concurrency behaviour - the graph, FastAPI, and the
MemorySaver checkpointer - from third-party API latency/limits. Check 3
is a small real burst against the live model chain, capped on purpose.

## 1. Concurrent distinct sessions (25 simultaneous conversations)

- Result: PASS
- Errors: 0/25
- Cross-session location mismatch: 0
- Latency: min=0.188s  median=0.262s  max=0.277s

## 2. Concurrent same session (10 simultaneous requests, one thread_id)

- Result: PASS
- Errors: 0/10
- Latency: min=0.079s  median=0.087s  max=0.094s

Honest note: a pass here means no crash and no corrupted state under a
same-thread race, not that the two concurrent turns are *semantically*
coherent with each other - that's an inherent race (whichever request's
state write lands last wins), not something this architecture tries to
resolve. For a single real user this is a non-issue (browsers serialise
their own requests); it would only matter for the double-click / two-tab
edge case, which is a UX concern (disable the input while pending, which
the Next.js and Streamlit frontends both already do), not a correctness
one.

## 3. Live burst against the real API + NVIDIA model chain

- Result: PASS
- Errors: 0/5
- Latency: min=12.476s  median=21.066s  max=38.331s

Deliberately capped at 5 concurrent requests: this hits a shared personal API key on a free/trial tier, not a dedicated load-testing account, so this is a modest-concurrency sanity check, not a capacity benchmark.
