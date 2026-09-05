import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "")
# Comma-separated, tried in order if the primary model errors or times out.
NVIDIA_FALLBACK_MODELS = [
    m.strip() for m in os.getenv("NVIDIA_FALLBACK_MODELS", "").split(",") if m.strip()
]
NVIDIA_TIMEOUT = float(os.getenv("NVIDIA_TIMEOUT", "45"))

SOP_FILE = ROOT / os.getenv("SOP_FILE", "sops/sops.yaml")

HTTP_TIMEOUT = 10
