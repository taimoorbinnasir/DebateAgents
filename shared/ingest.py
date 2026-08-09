import os
from .chunker import chunk_recursive, is_valid_chunk
from .memory import embedder, chroma
from .load_doc import load_pdf


def ingest_chunks(chunks: list[str], collection_name: str, source: str):
    col = chroma.get_or_create_collection(collection_name)
    for i, chunk in enumerate(chunks):
        embedding = embedder.encode(chunk).tolist()
        col.upsert(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{source}_{i}"],
            metadatas=[{"source": source, "chunk_index": i}]
        )


def ingest_document(filepath: str, collection_name: str, force: bool = False):
    """Ingest a document into ChromaDB. Skips if already ingested unless force=True."""
    col = chroma.get_or_create_collection(collection_name)
    
    # Skip re-ingestion unless forced — 1500 chunks takes time
    existing = col.count()
    if existing > 0 and not force:
        print(f"Collection '{collection_name}' already has {existing} chunks. Skipping ingestion.")
        return
    
    text = load_pdf(filepath)
    chunks = chunk_recursive(text)
    chunks = [c for c in chunks if is_valid_chunk(c)]  # filter artifacts
    
    print(f"Ingesting {len(chunks)} chunks from {filepath}...")
    
    # Batch upsert — faster than one-by-one
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        embeddings = embedder.encode(batch).tolist()  # batch encode is faster
        col.upsert(
            documents=batch,
            embeddings=embeddings,
            ids=[f"{os.path.basename(filepath)}_{i+j}" for j in range(len(batch))],
            metadatas=[{
                "source": os.path.basename(filepath),
                "chunk_index": i + j,
                "char_count": len(chunk)
            } for j, chunk in enumerate(batch)]
        )
        print(f"  {min(i+batch_size, len(chunks))}/{len(chunks)} chunks ingested")
    
    print(f"Done. Collection '{collection_name}' has {col.count()} chunks.")