import hashlib
from pathlib import Path
from dotenv import load_dotenv

# Load the project's .env explicitly (ANTHROPIC_API_KEY, SERP_API_KEY, MODEL_EVAL_API_KEY).
# Every entry point imports this module, so keys no longer depend on an incidental import
# chain reaching shared/tools.py. Absolute path → works from any working directory.
# Doesn't override variables already set in the environment.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Basic
MODEL = "claude-haiku-4-5"
MAX_TOKENS = 500
MEMORY_DB_PATH = "./memory_db"
COLLECTION_NAME = "agent_memory"

# ===================== MODELS PER ROLE =====================
# Every LLM call in a simulation belongs to one role. A profile maps each role to a model.
ROLES = (
    "draft",             # team mode: each member's private proposal
    "critique",          # team mode: each member's critique of the proposals
    "synthesis",         # team mode: presenter's single public statement
    "agent_turn",        # individual mode: one agent's public statement
    "moderator",         # per-round moderator summary
    "extremity_scorer",  # per-statement extremity score
    "position_scorer",   # per-round batched position scores
    "report",            # final analysis report
)

DEFAULT_PROFILE = "all_haiku"

# "Judges" grade the debate or steer it from outside (the moderator's summary goes into the
# shared history). They stay on ONE model in every profile, so a comparison changes only who
# debates — not who grades. Profile names describe the debating roles.
JUDGE_ROLES = ("moderator", "extremity_scorer", "position_scorer", "report")
JUDGE_MODEL = "claude-haiku-4-5"


def _profile(debater_model: str) -> dict:
    return {role: JUDGE_MODEL if role in JUDGE_ROLES else debater_model for role in ROLES}


MODEL_PROFILES = {
    "all_haiku":  _profile("claude-haiku-4-5"),  # default — current behavior
    "all_sonnet": _profile("claude-sonnet-5"),   # Sonnet debaters, Haiku judges
    "all_opus":   _profile("claude-opus-5-5"),   # Opus debaters, Haiku judges
}

# Extra request options per model. Sonnet 5 and Opus 5.5 think by default, and thinking
# tokens count against max_tokens (which stays unchanged per call site), so thinking is
# minimized: disabled on Sonnet 5; Opus 5.5 can't disable it, so effort "low" is the floor.
MODEL_REQUEST_OPTIONS = {
    "claude-haiku-4-5": {},
    "claude-sonnet-5":  {"thinking": {"type": "disabled"}},
    "claude-opus-5-5":  {"output_config": {"effort": "low"}},
}

# Extra max_tokens for models that still think. Opus 5.5 thinks even at effort "low", and
# thinking counts against max_tokens: in the pilot, all 6 Opus critiques (max_tokens=300) hit
# the cap with only 18-83 visible words (Haiku: 118-171). The allowance covers thinking only,
# so every model keeps the same room for its visible answer. Unused allowance costs nothing.
THINKING_ALLOWANCE = {
    "claude-opus-5-5": 1000,
}


def get_model(role: str, profile: str) -> str:
    if profile not in MODEL_PROFILES:
        raise ValueError(f"Unknown model profile '{profile}'. Known profiles: {sorted(MODEL_PROFILES)}")
    if role not in MODEL_PROFILES[profile]:
        raise ValueError(f"Unknown role '{role}' for profile '{profile}'. Known roles: {list(ROLES)}")
    return MODEL_PROFILES[profile][role]


# ===================== PRICING =====================
# USD per million tokens. UNVERIFIED: taken from third-party sources — check against
# Anthropic's official pricing page before relying on cost figures.
PRICING = {
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-5":  {"input": 2.00, "output": 10.00},
    "claude-opus-5-5":  {"input": 4.00, "output": 20.00},
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in PRICING:
        raise ValueError(f"No pricing for model '{model}'. Add it to PRICING in shared/config.py")
    rates = PRICING[model]
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000

# Debate sim settings (you'll use these in Week 5)
NUM_ROUNDS = 10
NUM_PRO_AGENTS = 3
NUM_CON_AGENTS = 3

LANGUAGE_INSTRUCTION = """
Use plain, everyday language. Avoid jargon, academic phrasing, and complex sentence
structure. Write so a general audience with no background in this topic can follow
your argument easily. Short sentences. Simple words. Keep the same conviction and
personality — just say it plainly.
"""


def topic_key(topic: str) -> str:
    return hashlib.md5(topic.lower().strip().encode()).hexdigest()[:8]