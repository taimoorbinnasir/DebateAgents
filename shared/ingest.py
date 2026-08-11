import os
from .chunker import chunk_recursive, is_valid_chunk
from .memory import embedder, chroma
from .load_doc import load_pdf
from .web_rag import save_agent_resources
from .search import build_search_query, search_web, fetch_url_content


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


def ingest_chunks_raw(chunks: list[str], collection_name: str, metadatas: list[dict]):
    """Ingest pre-chunked text directly — no file needed."""
    col = chroma.get_or_create_collection(collection_name)
    embeddings = embedder.encode(chunks).tolist()
    col.upsert(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"{collection_name}_{i}" for i in range(len(chunks))],
        metadatas=metadatas
    )


# IMPORTANT NOTE:
# Current ingestion process is based on filename. This allows multiple files from
# the same collection be ingested. However, the current approach faces 2 issues:
#   1) It will re-ingest the same file if the filename is different, even if the
#      content is the same.
#   2) It will not re-ingest a file if the filename is the same but the content
#      is different.
# The solution is to compute a hash of the file content and use that as the unique
# identifier instead of the filename. This will ensure that the ingestion process
# is based on the actual content of the document, preventing duplicates and ensuring
# updates are captured.
def ingest_document(filepath: str, collection_name: str, force: bool = False):
    col = chroma.get_or_create_collection(collection_name)
    doc_tag = os.path.basename(filepath)
    
    # Check if THIS specific document is already ingested
    existing = col.get(where={"source": doc_tag})
    if existing["ids"] and not force:
        print(f"'{doc_tag}' already ingested ({len(existing['ids'])} chunks). Skipping.")
        return
    
    text = load_pdf(filepath)
    chunks = chunk_recursive(text)
    chunks = [c for c in chunks if is_valid_chunk(c)]
    
    print(f"Ingesting {len(chunks)} chunks from {doc_tag}...")
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        embeddings = embedder.encode(batch).tolist()
        col.upsert(
            documents=batch,
            embeddings=embeddings,
            ids=[f"{doc_tag}_{i+j}" for j in range(len(batch))],
            metadatas=[{
                "source": doc_tag,
                "chunk_index": i + j,
                "char_count": len(chunk)
            } for j, chunk in enumerate(batch)]
        )
        print(f"  {min(i+batch_size, len(chunks))}/{len(chunks)} chunks ingested")
    
    print(f"Done. '{doc_tag}' ingested into '{collection_name}'.")



# Search web, fetch content, ingest into agent's private collection
def ingest_agent_sources(agent_id: str, topic: str):
    # ---------------------------- WEB SEARCH ----------------------------
    # ------ Check if topic already ingested
    collection_name = f"agent_{agent_id}_sources"
    col = chroma.get_or_create_collection(collection_name)
    
    # Skip if already ingested for this topic
    existing = col.get(where={"topic": topic})
    if existing["ids"]:
        print(f"  {agent_id}: sources already ingested for topic '{topic}'")
        return

    # ------ Build search query and search
    query = build_search_query(agent_id, topic)
    print(f"  {agent_id} searching: '{query}'")
    results = search_web(query, n_results=3)
    save_agent_resources(agent_id, topic, results)


    # ------ Fetch search results content
    all_chunks = []
    sources = []
    for r in results:
        # Use snippet as minimum content
        content = r["snippet"]
        
        # Try to fetch full page content
        if r["link"]:
            full_content = fetch_url_content(r["link"])
            if len(full_content) > len(content):  # only use if we got more content
                content = full_content
        
        # If content too short to chunk, use snippet directly as one chunk
        chunks = chunk_recursive(content, size=400)
        chunks = [c for c in chunks if is_valid_chunk(c)]
        
        if not chunks and len(content) > 50:  # fallback: use raw snippet as chunk
            chunks = [content]
        
        all_chunks.extend([(c, r["title"], r["link"]) for c in chunks])
        sources.append(r["title"])


    
    if not all_chunks:
        print(f"  {agent_id}: no valid content found")
        return

    # ---------------------------- INGESTION ----------------------------
    # Ingest into agent's private collection
    texts = [c[0] for c in all_chunks]
    embeddings = embedder.encode(texts).tolist()
    
    col.upsert(
        documents=texts,
        embeddings=embeddings,
        ids=[f"{agent_id}_{i}" for i in range(len(texts))],
        metadatas=[{
            "agent": agent_id,
            "topic": topic,
            "source_title": c[1],
            "source_url": c[2],
            "chunk_index": i
        } for i, c in enumerate(all_chunks)]
    )
    
    print(f"  {agent_id}: ingested {len(texts)} chunks from {len(results)} sources: {sources}")