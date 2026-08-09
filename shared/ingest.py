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