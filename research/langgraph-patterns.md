# LangGraph Patterns for a Policy-Grounded Weather Advisory Agent

Research notes only — no implementation. Focused on the building blocks needed for a real branching graph with session memory: `StateGraph`, conditional edges, tool-calling nodes, and checkpointers.

## 1. Core building blocks

### StateGraph
`StateGraph` is the graph builder class in LangGraph. You define a state schema (a `TypedDict` or Pydantic model) that is threaded through every node; each node receives the current state and returns a partial update that gets merged in.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

workflow = StateGraph(MyState)
workflow.add_node("retrieve_weather", retrieve_weather_node)
workflow.add_node("match_policy", match_policy_node)
workflow.add_node("handle_no_match", no_match_node)
workflow.add_node("compose_answer", compose_answer_node)
```

Source: [StateGraph reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph), [LangGraph in Production](https://www.kalviumlabs.ai/blog/langgraph-in-production-stateful-multi-step-agents/)

### Nodes
A node is just a Python function `(state) -> partial_state_update`. Nodes can call APIs (e.g., Open-Meteo), call the LLM, or do pure logic (e.g., policy matching). Keeping "fetch weather," "match policy," and "compose answer" as separate nodes is exactly the kind of decomposition that produces a *real* graph rather than one prompt wrapped in LangGraph's syntax — each node has a single responsibility and the edges express the actual control flow.

### Conditional edges (real branching)
A conditional edge does not connect two nodes directly — after a node runs, LangGraph calls a **router function** that reads the state and returns the name of the next node (or one of several names). This is what produces genuine branching instead of a linear chain.

```python
def route_after_policy_match(state) -> str:
    if state.get("api_error"):
        return "handle_api_error"
    if not state.get("matched_sops"):
        return "handle_no_match"
    return "compose_answer"

workflow.add_conditional_edges(
    "match_policy",
    route_after_policy_match,
    {
        "handle_api_error": "handle_api_error",
        "handle_no_match": "handle_no_match",
        "compose_answer": "compose_answer",
    },
)
```

Source: [LangGraph Basics: Conditional Edges & Routing Logic](https://shafiqulai.github.io/blogs/blog_10.html), [LangGraph Simplified — Conditional Edges (Medium)](https://medium.com/@Shamimw/langgraph-simplified-understanding-conditional-edge-using-hotel-guest-check-in-process-36adfe3380a8)

### Tool-calling nodes / ToolNode
LangGraph has a dedicated `ToolNode` type for executing tools (functions decorated with `@tool`) without hand-writing wrapper/dispatch logic. Typical pattern: an LLM/agent node decides whether a tool call is needed (e.g., "does this question require live weather data?"); if `tool_calls` are present in the LLM output, route to the `ToolNode`; otherwise route straight to response composition.

```python
# conceptual sketch from LangGraph tool-calling tutorials
if agent_output.tool_calls:
    next_node = "tools"
else:
    next_node = "respond"
```

Sources: [Building Tool Calling Agents with LangGraph (Medium)](https://sangeethasaravanan.medium.com/building-tool-calling-agents-with-langgraph-a-complete-guide-ebdcdea8f475), [DataCamp LangGraph Agents Tutorial](https://www.datacamp.com/tutorial/langgraph-agents), [Agentic RAG with LangGraph — Tools, Routing, Control (Medium)](https://medium.com/@renswick.d/rag-series-part-3-agentic-rag-with-langgraph-tools-routing-and-control-7b0b3e15eb43), [LangChain docs: custom RAG agent](https://docs.langchain.com/oss/python/langgraph/agentic-rag)

## 2. Checkpointers and session memory (multi-turn)

- A **checkpoint** is a snapshot of the entire graph state at a point in time, keyed by a monotonically increasing ID.
- A **thread** groups checkpoints together; every run against a checkpointer must supply a `thread_id` in the run config. This `thread_id` is what identifies "one chat session" — reusing it across calls gives the graph its memory of prior turns.
- `MemorySaver` is the simplest checkpointer — in-process, in-memory, good for a dev/take-home project (not for multi-process production, where you'd want a SQLite/Postgres/Redis-backed checkpointer instead).

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "session-123"}}
graph.invoke({"messages": [("user", "Is it safe to cycle today in Pune?")]}, config)
# Later turn, same thread_id -> graph remembers prior state/messages
graph.invoke({"messages": [("user", "What about this evening?")]}, config)
```

- Checkpointers are described as providing **short-term, thread-scoped memory** (conversation continuity within a session), distinct from **long-term memory** (facts persisted *across* sessions/threads, which needs a separate store). For a single-session take-home bot, thread-scoped checkpointing via `MemorySaver` is the relevant mechanism — no long-term store is required unless cross-session memory is explicitly wanted.
- `thread_id` values should stay under ~255 characters; a UUID or hash is recommended if a deterministic ID is needed.

Sources: [LangGraph Persistence concepts (LangChain docs)](https://docs.langchain.com/oss/python/langgraph/persistence), [langgraph.checkpoint reference](https://reference.langchain.com/python/langgraph.checkpoint), [checkpoints reference](https://reference.langchain.com/python/langgraph/checkpoints), [LangGraph persistence source on GitHub](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/concepts/persistence.md), [Memory docs (LangChain, JS variant but same concepts)](https://docs.langchain.com/oss/javascript/langgraph/add-memory), [Managing Threads and Conversation History (Medium)](https://medium.com/@m.naufalrizqullah17/managing-threads-and-conversation-history-in-langchain-with-checkpoints-df7b02beb321)

## 3. A graph shape matching "retrieve → match → handle no-match/error → compose"

This shape is a natural fit for LangGraph's conditional-edge model. A commonly seen pattern (adapted from agentic-RAG tutorials, where "retrieve → grade relevance → rewrite-or-generate" is the analogous shape):

```
START
  → parse_question (extract activity, location, timeframe from user turn + memory)
  → retrieve_weather (call Open-Meteo; on failure set state.api_error)
      -- conditional edge --
      ├─ api_error=True  → handle_api_error → compose_answer (honest "API unreachable")
      └─ api_error=False → match_policy (match question+data against SOP set)
                              -- conditional edge --
                              ├─ no SOPs matched → handle_no_match → compose_answer
                              └─ SOP(s) matched  → compose_answer (grounded in matched SOP + real numbers)
  → END
```

The RAG analog: "if not relevant, rewrite the question and call the agent again; if relevant, proceed to generate the final response" — i.e., a real graph has **multiple exit paths converging on a shared composition step**, not a single straight line. That's the structural signature reviewers look for to confirm "this is actually LangGraph, not a labeled linear chain."

Source: [Agentic RAG with LangGraph tutorial](https://medium.com/@renswick.d/rag-series-part-3-agentic-rag-with-langgraph-tools-routing-and-control-7b0b3e15eb43), [LangChain custom RAG agent docs](https://docs.langchain.com/oss/python/langgraph/agentic-rag)

## 4. Type of state schema: TypedDict vs Pydantic

- `TypedDict` — lightweight, zero runtime validation cost, common for LangGraph state when you're prototyping quickly and trust internal producers of state.
- Pydantic `BaseModel` — adds runtime validation/coercion and auto JSON-schema generation; worth it at boundaries where data enters from outside the trusted path (e.g., raw LLM structured output, external API responses).
- A practical middle ground raised in the LangGraph ecosystem: use `TypedDict` for the graph state itself (cheap, many updates/merges) but use Pydantic models for validating the *shape of individual node outputs* that cross a trust boundary (e.g., the weather API response, or an LLM's structured "matched SOP ids" output).

Sources: [Type Safety in LangGraph: TypedDict vs Pydantic](https://shazaali.substack.com/p/type-safety-in-langgraph-when-to), [Pydantic Models docs](https://pydantic.dev/docs/validation/dev/concepts/models/)

## 5. Notes for this project (research framing only)

- The brief's "retrieve data → match policy → handle no-match/error → compose answer" shape maps directly onto LangGraph nodes + conditional edges as shown above — this is a genuine, reviewable multi-branch graph, not a single call.
- Session memory requirement ("multi-turn context within one chat session") maps directly onto a `checkpointer` (e.g. `MemorySaver`) + a stable `thread_id` per chat session — no custom memory code needed, LangGraph provides this natively.
- None of this dictates *how* policy matching happens inside the `match_policy` node — that's covered separately in `policy-as-data-design.md`.
