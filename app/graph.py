"""The LangGraph wiring.

                          ┌─ refuse_override ────────────┐
                          ├─ ask_location ───────────────┤
  START ─ interpret ──────┼─ report_no_guidance ─────────┤
                          │                              │
                          └─ fetch ─┬─ report_unavailable ┤
                                    │                     │
                                    └─ match ─┬─ report_no_guidance
                                              │           │
                                              └─ compose ─ verify
                                                            │
                                       report_verification_failure
                                                            │
                                              record_turn ─ END

Five terminal paths reach the user, four of which are refusals. The failure
branches are real edges, not an exception handler wrapped around a happy path:
whether the location resolved, whether the API answered, whether any policy
matched and whether the draft survived validation are each a separate routing
decision on graph state.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app import nodes
from app.state import AdvisoryState

TERMINALS = {
    "ask_location": nodes.ask_location_node,
    "report_unavailable": nodes.report_unavailable_node,
    "report_no_guidance": nodes.report_no_guidance_node,
    "refuse_override": nodes.refuse_override_node,
    "report_verification_failure": nodes.report_verification_failure_node,
}


def build_graph(checkpointer=None):
    builder = StateGraph(AdvisoryState)

    builder.add_node("interpret", nodes.interpret_node)
    builder.add_node("fetch", nodes.fetch_node)
    builder.add_node("match", nodes.match_node)
    builder.add_node("compose", nodes.compose_node)
    builder.add_node("verify", nodes.verify_node)
    builder.add_node("record_turn", nodes.record_turn_node)
    for name, fn in TERMINALS.items():
        builder.add_node(name, fn)

    builder.add_edge(START, "interpret")

    builder.add_conditional_edges(
        "interpret",
        nodes.route_after_interpret,
        {
            "refuse_override": "refuse_override",
            "ask_location": "ask_location",
            "report_no_guidance": "report_no_guidance",
            "fetch": "fetch",
        },
    )

    builder.add_conditional_edges(
        "fetch",
        nodes.route_after_fetch,
        {"report_unavailable": "report_unavailable", "match": "match"},
    )

    builder.add_conditional_edges(
        "match",
        nodes.route_after_match,
        {"compose": "compose", "report_no_guidance": "report_no_guidance"},
    )

    builder.add_edge("compose", "verify")

    builder.add_conditional_edges(
        "verify",
        nodes.route_after_verify,
        {
            "report_verification_failure": "report_verification_failure",
            "done": "record_turn",
        },
    )

    for name in TERMINALS:
        builder.add_edge(name, "record_turn")

    builder.add_edge("record_turn", END)

    return builder.compile(checkpointer=checkpointer or MemorySaver())


_app = None


def get_app():
    """Process-wide graph. The MemorySaver lives here, so session memory
    survives across turns but resets when the process restarts, which is what
    the brief asks for."""
    global _app
    if _app is None:
        _app = build_graph()
    return _app


def ask(question, thread_id="default", app=None):
    """Run one turn and return the answer with its citation and audit trail."""
    app = app or get_app()
    result = app.invoke(
        {"question": question, "trace": []},
        config={"configurable": {"thread_id": thread_id}},
    )
    return {
        "answer": result.get("answer") or "",
        "citation": result.get("citation") or {},
        "trace": result.get("trace") or [],
        "interpretation": result.get("interpretation") or {},
    }
