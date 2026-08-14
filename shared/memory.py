import chromadb
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




# Get or create a private ChromaDB collection for an agent
def get_agent_collection(agent_name: str):
    return chroma.get_or_create_collection(f"agent_{agent_name}_memory")


# Store an agent's statement in their private memory collection
def store_agent_statement(agent_id: str, statement: str, round_num: int):
    agent_name = AGENT_PARAMS[agent_id]["name"]
    col = get_agent_collection(agent_name)
    embedding = embedder.encode(statement).tolist()
    col.upsert(
        documents=[statement],
        embeddings=[embedding],
        ids=[f"{agent_name}_round_{round_num}"],
        metadatas=[{
            "round": round_num,
            "agent": agent_name,
            "agent_id": agent_id
        }]
    )


# Retrieve an agent's own past statements relevant to a query
def recall_agent_history(agent_id: str, query: str, n: int = 3) -> list[str]:
    agent_name = AGENT_PARAMS[agent_id]["name"]
    col = get_agent_collection(agent_name)
    
    if col.count() == 0:
        return []
    
    embedding = embedder.encode(query).tolist()
    results = col.query(
        query_embeddings=[embedding],
        n_results=min(n, col.count()),
        include=["documents", "metadatas"]
    )
    return results["documents"][0] if results["documents"][0] else []