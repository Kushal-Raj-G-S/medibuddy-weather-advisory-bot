"""Thin HTTP wrapper around app/graph.py for the Next.js frontend.

Deliberately thin: no business logic lives here. It exists only because the
graph, the SOP loader and every guardrail are already built and tested in
Python, and a browser cannot import a Python module directly. Every rule
about traceability and grounding is enforced upstream in app/nodes.py and
app/validation.py exactly as before - this file just puts JSON in front of it.

Run:  uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.graph import ask as run_ask
from app.sop_loader import SOPFileError, load_policy

app = FastAPI(title="Weather Advisory Bot API")

app.add_middleware(
    CORSMiddleware,
    # The Next.js dev server's port can shift (auto-assigned if 3000 is taken),
    # so any localhost port is allowed in development rather than one fixed
    # origin.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    thread_id: str = "default"


class AskResponse(BaseModel):
    answer: str
    citation: dict
    interpretation: dict
    trace: list


@app.post("/api/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    question = payload.question.strip()
    if not question:
        raise HTTPException(400, "question must not be empty")
    result = run_ask(question, thread_id=payload.thread_id)
    return AskResponse(**result)


@app.get("/api/policy")
def policy():
    """Read-only summary the sidebar renders. Never used by the graph itself -
    it exists purely so the UI can show what's loaded, live, from the same
    file the graph reads."""
    try:
        p = load_policy(force=True)
    except SOPFileError as exc:
        raise HTTPException(500, str(exc)) from exc

    return {
        "count": len(p.sops),
        "categories": sorted({s.category for s in p.sops}),
        "sops": [
            {
                "id": s.id,
                "title": s.title,
                "category": s.category,
                "severity": s.severity,
                "override": s.override,
                "judgment_based": s.is_judgment_based,
            }
            for s in p.sops
        ],
    }


@app.get("/api/health")
def health():
    return {"ok": True}
