"""Minimal chat frontend. Deliberately unstyled: the reviewable part is the
citation panel under each reply, which shows which SOP produced the answer and
which fetched values it was allowed to quote.

Run from the repo root:  streamlit run frontend/streamlit_app.py
"""

import sys
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph import ask  # noqa: E402
from app.sop_loader import load_policy  # noqa: E402

st.set_page_config(page_title="Weather Advisory Bot", page_icon="⛅")
st.title("Weather-Advisory Support Bot")
st.caption(
    "Every answer is either traceable to a written SOP or an explicit refusal."
)

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.subheader("Session")
    st.write(f"Thread: `{st.session_state.thread_id[:8]}`")
    if st.button("New session"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.history = []
        st.rerun()

    st.subheader("Loaded policy set")
    try:
        policy = load_policy()
        st.write(f"{len(policy.sops)} SOPs across "
                 f"{len({s.category for s in policy.sops})} categories")
        for sop in policy.sops:
            st.caption(f"`{sop.id}` {sop.title} — {sop.severity}")
        st.info("Edit sops/sops.yaml and just ask again — it reloads on change.")
    except Exception as exc:  # noqa: BLE001 - surface any policy file error
        st.error(f"Policy file problem: {exc}")

for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.write(turn["content"])
        if turn.get("citation"):
            citation = turn["citation"]
            if citation.get("sop_id"):
                label = f"Source: {citation['sop_id']} ({citation['severity']})"
            else:
                label = f"No SOP cited — {citation.get('reason', 'n/a')}"
            with st.expander(label):
                st.json(citation)
        if turn.get("trace"):
            with st.expander("Decision trace"):
                st.json(turn["trace"])

question = st.chat_input("Ask about an outdoor activity, e.g. 'is it safe to cycle in Bhopal today?'")

if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Checking policy and live conditions..."):
            try:
                result = ask(question, thread_id=st.session_state.thread_id)
            except Exception as exc:  # noqa: BLE001 - never crash the chat surface
                result = {
                    "answer": f"Something went wrong handling that: {exc}",
                    "citation": {"sop_id": None, "reason": "internal_error"},
                    "trace": [],
                }
        st.write(result["answer"])
        st.session_state.history.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "citation": result["citation"],
                "trace": result["trace"],
            }
        )
        st.rerun()
