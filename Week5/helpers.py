import sys, os
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.agents import AGENT_PARAMS
from shared.memory import embedder

def get_last_opponent_statement(agent_id: str, shared_history: list) -> str:
    my_stance = AGENT_PARAMS[agent_id]["stance"]
    for msg in reversed(shared_history):
        for other_id, other_config in AGENT_PARAMS.items():
            if (other_config["stance"] != my_stance and
                    msg.startswith(other_config["name"] + ":")):
                return msg
    return ""

def get_last_ally_statement(agent_id: str, shared_history: list) -> str:
    my_stance = AGENT_PARAMS[agent_id]["stance"]
    my_name = AGENT_PARAMS[agent_id]["name"]
    for msg in reversed(shared_history):
        for other_id, other_config in AGENT_PARAMS.items():
            if (other_config["stance"] == my_stance and
                    other_config["name"] != my_name and
                    msg.startswith(other_config["name"] + ":")):
                return msg
    return ""


# ===================== STOPPING CONDITIONS =====================
def should_stop(shared_history: list, round_num: int, max_rounds: int) -> tuple[bool, str]:
    if round_num >= max_rounds:
        return True, f"Maximum rounds ({max_rounds}) reached"

    # Repetition detection after round 4
    if round_num >= 4:
        n = len(AGENT_PARAMS)
        recent  = shared_history[-(n * 2):]
        earlier = shared_history[-(n * 4):-(n * 2)]

        if recent and earlier:
            r_emb = embedder.encode(" ".join(recent))
            e_emb = embedder.encode(" ".join(earlier))
            similarity = np.dot(r_emb, e_emb) / (
                np.linalg.norm(r_emb) * np.linalg.norm(e_emb)
            )
            if similarity > 0.92:
                return True, f"Conversation converged (similarity: {similarity:.2f})"

    return False, ""


# Strip refusal/meta lines so they don't pollute agent context
def clean_history(shared_history: list) -> list:
    skip_phrases = ["i cannot", "i'm unable", "as an ai", "i won't", "i must clarify"]
    return [
        msg for msg in shared_history
        if not any(phrase in msg.lower() for phrase in skip_phrases)
    ]


# Given a message like 'Aggro: ...', find which agent_id spoke it
def extract_agent_id_from_message(message: str) -> str | None:
    if not message:
        return None
    speaker_name = message.split(":")[0].strip()
    for agent_id, config in AGENT_PARAMS.items():
        if config["name"] == speaker_name:
            return agent_id
    return None