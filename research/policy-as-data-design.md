# Policy-as-Data: Decoupling SOPs from Control-Flow Code

Research notes only. Covers rules-engine patterns, semantic vs keyword matching for routing free-text questions to rules, "LLM as classifier over external policy docs" patterns, RAG-lite for small fixed rule sets, hot-reload, and representation tradeoffs.

## 1. Why decouple rules from code (rules-engine pattern)

A rules engine externalizes business/decision logic (conditions + actions) into a structured file so it can be executed, inspected, and edited **without touching the application code that evaluates it**. The commonly cited shape is: a `conditions` field describing what triggers the rule, and an `actions`/`outcome` field describing what happens when it's satisfied.

Key claimed benefits from multiple sources:
- Non-developers (or a "policy owner") can update rules without a code deploy.
- Faster iteration — rule changes take effect without redeploying application logic.
- Cleaner separation of "what the policy says" from "how the system fetches data and talks to the LLM."

This maps directly onto the brief's hard requirement: SOPs must be editable — including adding an 11th SOP live — without touching the weather-fetching or LLM-calling code.

Sources: [Introduction to JSON Rules Engine (Medium)](https://medium.com/@riadh.mouamnia/introduction-to-json-rules-engine-3bea7b6a8eec), [JSON Rules Engine: Separate Logic From Code (FlowWright)](https://www.flowwright.com/json-rules-engine-separate-logic-from-code), [Rule Engine Design Pattern (Nected)](https://www.nected.ai/blog/rules-engine-design-pattern), [How Rule Engines Transform Business Agility (Capestart)](https://capestart.com/technology-blog/how-rule-engines-transform-business-agility-and-code-simplicity/), [The Power of Decoupling: JSON Rules Engine (Medium)](https://medium.com/@monish.krishnan.icdi/the-power-of-decoupling-lessons-from-json-rules-engine-f5765146c504)

## 2. Keyword matching vs semantic/intent matching for routing free text to a rule

The brief explicitly requires at least one **fuzzy, non-numeric SOP** (e.g. "is today good for a picnic?") that cannot reduce to a simple `if x > y` threshold, and requires the bot to handle **paraphrased** questions that don't hit obvious keywords. This makes pure keyword/string matching insufficient as the sole mechanism.

### Approaches found in research
1. **Keyword/regex matching** — simplest, fully deterministic, cheap, but brittle against paraphrase (fails the "paraphrased/non-keyword match" eval case in the brief almost by definition).
2. **Semantic routing via embeddings** — precompute embedding vectors for each SOP's seed utterances/description; at query time, embed the user's question and do nearest-neighbor / cosine-similarity lookup against the fixed route set. Cited as "very fast" and "deterministic" once routes are precomputed — good fit for a **small, fixed** rule set (10+ SOPs, not thousands), and much cheaper than a full LLM call per turn. Introduces "stability and reliability... through deterministic decision-making" versus letting a standalone LLM freely decide, while still avoiding hallucination of routes that don't exist.
3. **LLM-as-classifier/router** — feed the user's question (and the list of SOP titles/short descriptions) to the LLM and ask it to output which SOP id(s), if any, apply — essentially "LLM as classifier over an external policy index" rather than the LLM freely inventing advice. This handles fuzzy/non-numeric SOPs naturally (an LLM can judge "is this a good picnic day" against a written qualitative SOP) but is less deterministic than embeddings and costs a model call.
4. **Lightweight fine-tuned classifier** (e.g., a small BERT-family model fine-tuned on intent labels) — mentioned as fast/CPU-friendly for real-time inline inference; more setup cost, likely overkill for a fixed set of ~10 SOPs in a take-home context, but noted here as an option.
5. **Definite Finite Automaton / DFA-based conversational routing** — an academic approach (DFA-RAG) combining an LLM with a deterministic finite-state layer for reliable multi-turn routing; more relevant to production research literature than a scoped take-home, included for completeness.

Sources: [Intent Recognition and Auto-Routing in Multi-Agent Systems (gist)](https://gist.github.com/mkbctrl/a35764e99fe0c8e8c00b2358f55cd7fa), [RAG Routers: Semantic Routing with LLMs and Tool Calling (Medium)](https://medium.com/@giacomo__95/rag-routers-semantic-routing-with-llms-and-tool-calling-b53dd8fae7fa), [DFA-RAG: Conversational Semantic Router (arXiv)](https://arxiv.org/pdf/2402.04411), [Semantic Routing for LLM-Assisted Intent Management (arXiv)](https://arxiv.org/pdf/2404.15869)

## 3. "LLM as classifier/router over external policy documents" — general pattern

Rather than letting the LLM generate advice from its own training knowledge, the LLM (or an embedding layer) is used purely to **select which pre-written policy text applies**, and then a separate step composes the final answer strictly from the matched policy text + the live data. This is the RAG-lite framing: instead of a full vector database + chunking pipeline (appropriate for large/unbounded corpora), a small fixed set of SOPs (~10-20) can be:
- Kept entirely in-context (all SOP text passed to the LLM every turn, letting it match directly) — simplest, no retrieval infra needed, works well until the rule set grows large enough to blow the context budget or dilute matching precision.
- Embedded once and matched via cosine similarity (RAG-lite / semantic router) — adds a small amount of infra but scales the matching decision better and is deterministic/inspectable, at the cost of needing an embedding model and a similarity threshold to decide "no SOP matches."

Both are valid "RAG-lite" strategies for a small fixed rule set — the distinction from full RAG is the corpus is small enough to not need chunking, indexing pipelines, or top-k retrieval infra; either "put it all in context" or "one flat embedding lookup" suffices.

Sources: [RAG Routers: Semantic Routing (Medium)](https://medium.com/@giacomo__95/rag-routers-semantic-routing-with-llms-and-tool-calling-b53dd8fae7fa), [LLM Selection and Vector DB Tuning for RAG (MDPI)](https://www.mdpi.com/2076-3417/15/20/10886)

## 4. Hot-reloadable policy files

For "edit SOPs without touching code, even live," the general Python pattern found:
- A **Config Loader** reads the rules file (JSON/YAML) at startup and on change; a **Validator** step checks the new file against an expected schema before it's accepted (important so a malformed live edit doesn't crash the running bot); a **Config Store** holds the currently active, validated rule set in memory; the **application** always reads rules from the store, never re-parsing the file mid-request.
- File-change detection commonly uses OS-level file-system notification APIs (e.g., `inotify` on Linux) via a library like Python's `watchdog` (`watchdog.observers.Observer` + `watchdog.events.FileSystemEventHandler`), with debouncing so multiple rapid saves (e.g., from an editor) don't trigger repeated reloads.
- A simpler alternative sufficient for a take-home / single-process app: just re-read and re-validate the rules file at the start of each request (or every N seconds) rather than running a background file-watcher thread — much less code, and "live edit visible on next question" satisfies the brief's "live 11th SOP" requirement without the complexity of a watcher.

Sources: [How to Implement Configuration Hot-Reload (OneUptime)](https://oneuptime.com/blog/post/2025-12-11-configuration-hot-reload/view), [How to Build a Config System with Hot Reload in Python (OneUptime)](https://oneuptime.com/blog/post/2026-01-22-config-hot-reload-python/view), [Config file watcher example (glama.ai)](https://glama.ai/mcp/servers/@roddutra/agent-mcp-gateway/blob/a1d664a4129bb6358b3cc9045f0095f2f32f127e/src/config_watcher.py)

## 5. Representation tradeoffs: JSON vs YAML vs Pydantic models vs embedded policy docs

| Representation | Pros | Cons |
|---|---|---|
| **Plain JSON rules file** | Language-agnostic, trivially parsed by any tool, easy `jq`-style inspection, unambiguous types | Verbose for humans to hand-edit (no comments, punctuation-heavy), easy to introduce a syntax error by hand |
| **YAML rules file** | Much friendlier for a human/policy-owner to hand-edit live (supports comments, less punctuation, multi-line text blocks good for prose SOP wording), still trivially parseable | Whitespace-sensitivity is a common source of subtle edit errors; slightly more parsing edge cases than JSON |
| **Pydantic models (validated at load time, regardless of source format)** | Runtime validation + coercion, clear error messages on malformed rule entries, auto-generates JSON Schema (useful for documenting the expected rule shape to whoever edits it), integrates naturally with a Python LangGraph node | Not itself a storage format — still needs an underlying file (JSON/YAML) that gets *loaded into* Pydantic; adds a dependency and a schema-definition step |
| **Vector-embedded policy docs (RAG-style, one embedding per SOP)** | Naturally handles fuzzy/paraphrased matching without a separate LLM router call; scales to larger rule sets | Overkill infra for ~10-20 SOPs; introduces a similarity-threshold tuning problem (”how close is close enough to count as a match?”) which itself becomes an undocumented, hard-to-edit implicit policy; less transparent/inspectable than a rule ID + written condition |

General Pydantic vs raw-dict tradeoff (useful when deciding how the loaded rules are represented in memory before being handed to the graph): Pydantic is "worth it at any boundary where data comes from outside your trusted process" (an edited YAML/JSON file *is* such a boundary), while a lighter `TypedDict`/dataclass is fine for purely internal, already-validated data with lower overhead.

Sources: [What Is Pydantic? (Netguru)](https://www.netguru.com/blog/data-validation-pydantic), [Pydantic Models docs](https://pydantic.dev/docs/validation/dev/concepts/models/), [Structured Output Validation: Pydantic vs JSON Schema](https://dasroot.net/posts/2026/02/structured-output-validation-pydantic-json-schema/), [Type Safety in LangGraph: TypedDict vs Pydantic](https://shazaali.substack.com/p/type-safety-in-langgraph-when-to)

## 6. Summary takeaway for this project's design question

The brief's two hardest constraints — (a) SOPs editable without touching control-flow code, and (b) at least one fuzzy/non-numeric SOP that can't reduce to a numeric threshold — together push toward a design where:
- Rules live in an external file (JSON or YAML) loaded and validated (e.g., via Pydantic) into memory, completely separate from the "fetch weather" / "call LLM" code paths.
- Matching a free-text question to a rule needs *some* semantic capability (keyword-only matching cannot handle fuzzy SOPs or paraphrase) — the open question is whether that semantic capability is "the LLM matches directly against in-context SOP text" or "embeddings + similarity threshold," both of which are legitimate RAG-lite choices for a rule set this small. This exact tradeoff is expanded with pros/cons in `brainstorm-summary.md`.
