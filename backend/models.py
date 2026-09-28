from pydantic import BaseModel, Field
from typing import Optional

# ── User opinion ──────────────────────────────────
class UserOpinion(BaseModel):
    round_num: int
    position:  int              # -10 to +10, same scale as agents
    comment:   Optional[str] = None

# ── Requests ──────────────────────────────────────
class SimulationRequest(BaseModel):
    topic: str
    max_rounds: int = 5
    mode: str = "individual"
    model_profile: str = "all_haiku"        # see shared/config.py MODEL_PROFILES
    seed:          Optional[int] = None     # reproducible turn/presenter order


# ── Per-message ────────────────────────────────────
class SourceCitation(BaseModel):
    title: str
    url:   str


class AgentStatement(BaseModel):
    agent_name:  str
    agent_id:    str
    stance:      str          # "pro" | "con"
    round_num:   int
    text:        str
    extremity:   int          # 1-10
    sources:    list[SourceCitation] = []


class ModeratorSummary(BaseModel):
    round_num: int
    text:      str


# ── Simulation state ───────────────────────────────
class SimulationStatus(BaseModel):
    session_id:    str
    topic:         str
    status:        str        # "running" | "complete" | "error"
    current_round: int
    max_rounds:    int
    stop_reason:   Optional[str] = None
    extremity_log: dict       # {agent_id: [scores]}
    position_log:    dict = {}
    influence_edges: list = []
    user_opinions:   list = []


class SimulationTranscript(BaseModel):
    session_id:    str
    topic:         str
    stop_reason:   str
    transcript:    list[str]
    extremity_log: dict
    mode:            str  = "individual"   # "individual" | "team"
    position_log:    dict = {}
    influence_edges: list = []
    user_opinions:   list = []
    statements:      list = []   # structured statements with sources
    presenter_log:   dict = {}   # team mode: {"pro": [agent_id per round], "con": [...]}
    brainstorm_log:  list = []   # team mode: per team per round drafts + critiques
    # Model comparison — absent on transcripts saved before these existed
    # `model_config` is reserved by Pydantic v2 (class configuration), so the attribute is
    # named differently and exposed/accepted under the alias "model_config"
    run_model_config: dict = Field(default_factory=dict, alias="model_config")  # {"profile", "roles"}
    cost_log:        list = []   # one entry per LLM call
    total_cost_usd:  Optional[float] = None
    experiment_id:   Optional[str] = None
    seed:            Optional[int] = None


# ── Simulation list item ───────────────────────────
class SimulationMeta(BaseModel):
    session_id: str
    topic:      str
    timestamp:  str
    rounds:     int
    stop_reason: Optional[str] = None
    mode:       str = "individual"
    saved_at:   Optional[str] = None   # ISO time; drives newest-first ordering