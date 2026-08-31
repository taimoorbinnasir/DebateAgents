from pydantic import BaseModel
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
    position_log:    dict = {}
    influence_edges: list = []
    user_opinions:   list = []


# ── Simulation list item ───────────────────────────
class SimulationMeta(BaseModel):
    session_id: str
    topic:      str
    timestamp:  str
    rounds:     int
    stop_reason: Optional[str] = None