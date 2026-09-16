import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer
from shared.agents import AGENT_PARAMS

# Runs locally, no API key, free
embedder = SentenceTransformer("all-mpnet-base-v2")

# PersistentClient saves to disk — survives process restarts
chroma = chromadb.PersistentClient(path="./memory_db")
collection = chroma.get_or_create_collection("agent_memory")


# Remembers facts about the user
def remember(fact: str, fact_id: str, metadata: dict = None):
    embedding = embedder.encode(fact).tolist()
    collection.upsert(
        documents=[fact],
        embeddings=[embedding],
        ids=[fact_id],
        **({"metadatas": [metadata]} if metadata else {})  # only pass if provided
    )

# Recalls facts about the user specific to the query
def recall(query: str, n: int = 3) -> list[str]:
    embedding = embedder.encode(query).tolist()
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n
    )
    return results["documents"][0]  # list of top-n matching facts




# Get or create a private ChromaDB collection for an agent that's isolated per session
def get_agent_memory_collection(agent_name: str, session_id: str):
    return chroma.get_or_create_collection(f"agent_{agent_name}_memory_{session_id}")

# Store an agent's statement in their private memory collection
def store_agent_statement(agent_id: str, statement: str, round_num: int, session_id: str):
    agent_name = AGENT_PARAMS[agent_id]["name"]
    col = get_agent_memory_collection(agent_name, session_id)
    embedding = embedder.encode(statement).tolist()
    col.upsert(
        documents=[statement],
        embeddings=[embedding],
        ids=[f"{agent_name}_round_{round_num}"],
        metadatas=[{"round": round_num, "agent": agent_name, "session_id": session_id}]
    )

def recall_agent_history(agent_id: str, query: str, session_id: str, n: int = 3) -> list[str]:
    agent_name = AGENT_PARAMS[agent_id]["name"]
    col = get_agent_memory_collection(agent_name, session_id)
    
    if col.count() == 0:
        return []
    
    embedding = embedder.encode(query).tolist()
    results = col.query(
        query_embeddings=[embedding],
        n_results=min(n, col.count()),
        include=["documents"]
    )
    return results["documents"][0] if results["documents"][0] else []



# ================================= SHARED TEAM MEMORY =================================
def get_team_channel_collection(team_name: str, session_id: str):
    """Private brainstorm space for one team, one session — the 3 agents on 
    this team can read each other's drafts here, opposing team cannot."""
    return chroma.get_or_create_collection(f"team_{team_name}_channel_{session_id}")

def store_team_draft(team_name: str, agent_id: str, draft: str, round_num: int, session_id: str):
    col = get_team_channel_collection(team_name, session_id)
    embedding = embedder.encode(draft).tolist()
    col.upsert(
        documents=[draft],
        embeddings=[embedding],
        ids=[f"{agent_id}_round_{round_num}"],
        metadatas=[{"agent_id": agent_id, "round": round_num, "team": team_name}]
    )

def get_team_drafts_for_round(team_name: str, round_num: int, session_id: str) -> list[dict]:
    """Retrieve all drafts submitted by this team for a specific round — 
    used by the presenter-selection step (Part 3)."""
    col = get_team_channel_collection(team_name, session_id)
    results = col.get(where={"round": round_num})
    return [
        {"agent_id": meta["agent_id"], "draft": doc}
        for doc, meta in zip(results["documents"], results["metadatas"])
    ]
# ======================================================================================


def verify_source_usage(reply_text: str, sources: list[dict], threshold: float = 0.35) -> list[dict]:
    """
    Filters retrieved sources down to only those whose content is 
    semantically close to what the agent actually said. 
    Uses cosine similarity — zero extra LLM calls.
    """
    if not sources:
        return []
    
    reply_embedding = embedder.encode(reply_text)
    verified = []
    
    for source in sources:
        source_embedding = embedder.encode(source["text"])
        similarity = np.dot(reply_embedding, source_embedding) / (
            np.linalg.norm(reply_embedding) * np.linalg.norm(source_embedding)
        )

        print(f"  Reply-to-source similarity: {similarity:.3f}")  # add this
        if similarity >= threshold:
            verified.append({
                **source,
                "similarity": round(float(similarity), 3)
            })
    
    return verified