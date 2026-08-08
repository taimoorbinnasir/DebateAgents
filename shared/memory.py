import chromadb
from sentence_transformers import SentenceTransformer

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