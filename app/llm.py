"""LLM access. Provider-agnostic on purpose: the brief leaves model choice open,
so the provider is an env switch and nothing else in the codebase knows which
model is in use.

The nvidia provider additionally chains a fallback list: if the primary model
errors, times out, or (some hosted NIM models) never returns a tool call for a
structured request, the next candidate in NVIDIA_FALLBACK_MODELS is tried. This
matters specifically for interpret_node and match_node's judge step, both of
which require reliable structured output - not every hosted model on that
endpoint supports it, so the fallback chain is a reliability guardrail, not
just a cost one.
"""

from functools import lru_cache

from app import config


def _anthropic(temperature):
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=config.ANTHROPIC_MODEL, temperature=temperature, max_tokens=1200
    )


def _openai(temperature):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=config.OPENAI_MODEL, temperature=temperature)


def _nvidia_candidates(temperature):
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    model_ids = [config.NVIDIA_MODEL, *config.NVIDIA_FALLBACK_MODELS]
    model_ids = [m for m in model_ids if m]
    if not model_ids:
        raise RuntimeError("LLM_PROVIDER=nvidia but no NVIDIA_MODEL is set")
    return [
        ChatNVIDIA(
            model=model_id,
            temperature=temperature,
            timeout=config.NVIDIA_TIMEOUT,
            max_tokens=1200,
        )
        for model_id in model_ids
    ]


@lru_cache(maxsize=4)
def _candidates(temperature=0.0):
    """Primary model first, then fallbacks. Single-element for non-nvidia
    providers, which is what makes with_fallbacks a no-op for them."""
    if config.LLM_PROVIDER == "openai":
        return (_openai(temperature),)
    if config.LLM_PROVIDER == "nvidia":
        return tuple(_nvidia_candidates(temperature))
    return (_anthropic(temperature),)


def get_llm(temperature=0.0):
    """The primary model, with the rest of the candidate list wired in as
    runtime fallbacks. Calling .invoke on the result tries each in order."""
    primary, *rest = _candidates(temperature)
    return primary.with_fallbacks(rest) if rest else primary


def structured(schema, temperature=0.0):
    """Bind a Pydantic schema so the model cannot return anything off-shape.

    Used for SOP selection: the id comes back inside a validated structure
    rather than as free text, which removes a whole class of "the model made up
    a policy id" failures at the transport level.

    Fallbacks are chained AFTER binding structured output to each candidate,
    because a model that cannot produce a valid tool call should fail over to
    the next one, not silently degrade to unstructured text.
    """
    primary, *rest = _candidates(temperature)
    bound = primary.with_structured_output(schema)
    if not rest:
        return bound
    return bound.with_fallbacks([m.with_structured_output(schema) for m in rest])


def complete(system, user, temperature=0.0):
    content = get_llm(temperature).invoke([("system", system), ("human", user)]).content

    if isinstance(content, str):
        return content.strip()

    # Anthropic returns a list of content blocks.
    parts = [
        block.get("text", "") if isinstance(block, dict) else str(block)
        for block in content or []
    ]
    return "".join(parts).strip()
