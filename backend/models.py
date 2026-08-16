from pydantic import BaseModel
from typing import Optional

# ── Requests ──────────────────────────────────────
class SimulationRequest(BaseModel):
    topic: str
    max_rounds: int = 5


# ── Per-message ────────────────────────────────────
class AgentStatement(BaseModel):
    agent_name:  str
    agent_id:    str
    stance:      str          # "pro" | "con"
    round_num:   int
    text:        str
    extremity:   int          # 1-10


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


class SimulationTranscript(BaseModel):
    session_id:    str
    topic:         str
    stop_reason:   str
    transcript:    list[str]
    extremity_log: dict


# ── Simulation list item ───────────────────────────
class SimulationMeta(BaseModel):
    session_id: str
    topic:      str
    timestamp:  str
    rounds:     int
    stop_reason: Optional[str] = None