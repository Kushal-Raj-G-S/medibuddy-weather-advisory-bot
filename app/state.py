from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AdvisoryState(TypedDict, total=False):
    # Raw turn history. The checkpointer persists this per thread, which is
    # what gives the bot session memory.
    messages: Annotated[list, add_messages]

    question: str

    # Structured reading of the current question.
    interpretation: dict

    # Carried-forward context so "what about this evening?" resolves without
    # making the user restate location or activity.
    session_facts: dict

    snapshot: Any
    failure: str

    matches: list
    primary: Any
    co_applying: list

    draft: str
    answer: str
    citation: dict

    # Append-only audit log of what each node decided.
    trace: list
