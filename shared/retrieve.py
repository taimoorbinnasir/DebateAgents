from .agents import AGENT_PARAMS
from .config import topic_key
from .memory import embedder, chroma

def retrieve_chunks(query: str, collection_name: str, n: int = 3) -> list[dict]:
    """Retrieve top-n chunks by cosine similarity with source citations."""
    col = chroma.get_or_create_collection(collection_name)
    
    if col.count() == 0:
        return []
    
    embedding = embedder.encode(query).tolist()
    results = col.query(
        query_embeddings=[embedding],
        n_results=n,
        include=["documents", "metadatas", "distances"]
    )
    
    return [
        {
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "distance": dist,
            "citation": f"{meta['source']}, chunk {meta['chunk_index']}"
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]


# Retrieve relevant chunks from agent's private source collection (Used in web_rag.py)
def retrieve_agent_sources(agent_id: str, query: str, topic: str, n: int = 2) -> list[dict]:
    agent_name = AGENT_PARAMS[agent_id]["name"]
    collection_name = f"agent_{agent_name}_sources_{topic_key(topic)}"
    col = chroma.get_or_create_collection(collection_name)

    print(f"DEBUG retrieve_agent_sources[{agent_id}]: collection={collection_name!r} count={col.count()} query={query!r}")  # add this

    if col.count() == 0:
        return []

    embedding = embedder.encode(query).tolist()
    results = col.query(
        query_embeddings=[embedding],
        n_results=n,
        include=["documents", "metadatas", "distances"]
    )

    if not results["documents"][0]:
        return []

    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        print(f"  DEBUG dist={dist:.4f} [{meta['source_title']}] {doc[:80]!r}")  # add this

    return [
        {
            "text": doc,
            "source_title": meta["source_title"],
            "source_url": meta["source_url"],
            "distance": dist,
            "citation": meta["source_title"]
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
        if dist < 1.2
    ]