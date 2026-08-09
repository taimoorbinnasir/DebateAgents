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