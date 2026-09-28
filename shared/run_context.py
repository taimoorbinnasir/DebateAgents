import os, random
from anthropic import Anthropic
from .config import (
    DEFAULT_PROFILE, MODEL_PROFILES, MODEL_REQUEST_OPTIONS,
    get_model, compute_cost
)

class RunContext:
    """
    Per-simulation state for LLM calls, passed explicitly through the call chain
    (simulations run in background threads, so no module-level globals).

    - profile:  which model each role uses (shared/config.py MODEL_PROFILES)
    - cost_log: one entry per LLM call, with real token usage from response.usage
    - rng:      random.Random(seed) when seeded, else the global random module (unseeded
                behavior is unchanged). Controls ordering only — LLM outputs stay nondeterministic.
    - api_key:  None → ANTHROPIC_API_KEY, as before. Lets a harness (e.g. model_eval, on its
                own workspace) use a different key per run without touching the environment.
    """

    def __init__(self, profile: str = DEFAULT_PROFILE, seed: int | None = None, api_key: str | None = None):
        if profile not in MODEL_PROFILES:
            raise ValueError(f"Unknown model profile '{profile}'. Known profiles: {sorted(MODEL_PROFILES)}")
        self.profile  = profile
        self.seed     = seed
        self.rng      = random.Random(seed) if seed is not None else random
        self.api_key  = api_key
        self.cost_log = []

    def create(self, role: str, round_num: int | None = None, agent_id: str | None = None, **request):
        """
        One messages.create call for `role`. A fresh Anthropic() client per call keeps
        each agent's API context isolated. `request` is passed through unchanged
        (system, messages, max_tokens) — only the model and per-model options are added.
        """
        model = get_model(role, self.profile)
        client = Anthropic(api_key=self.api_key or os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(model=model, **MODEL_REQUEST_OPTIONS.get(model, {}), **request)

        usage = response.usage
        self.cost_log.append({
            "role":          role,
            "model":         model,
            "round":         round_num,
            "agent_id":      agent_id,
            "input_tokens":  usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd":      compute_cost(model, usage.input_tokens, usage.output_tokens),
            # "max_tokens" here means the reply was cut off — watch for it on thinking models
            "stop_reason":   response.stop_reason,
        })
        return response

    def model_config(self) -> dict:
        return {"profile": self.profile, "roles": dict(MODEL_PROFILES[self.profile])}

    def total_cost(self) -> float:
        return sum(entry["cost_usd"] for entry in self.cost_log)


def response_text(response) -> str:
    """First text block. Thinking models put a thinking block first, so content[0] isn't
    always text; for models without thinking this is exactly content[0].text."""
    return next((block.text for block in response.content if block.type == "text"), "")
