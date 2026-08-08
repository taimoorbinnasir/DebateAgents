import numpy as np
import pypdf, fitz          # fitz = pymupdf
import sys, os, requests, re
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.memory import embedder, chroma


def load_pdf(filepath: str) -> str:
    doc = fitz.open(filepath)
    pages = []
    for page in doc:
        text = page.get_text("text")  # better extraction than pypdf
        if not text or len(text.strip()) < 50:
            continue
        # Fix hyphenation only
        text = re.sub(r'-\n', '', text)
        text = re.sub(r'\n(?=[a-z])', ' ', text)
        lines = [l for l in text.split("\n")
                 if len(l.strip()) > 20
                 and not l.strip().replace(".", "").replace(" ", "").isdigit()
                 and "....." not in l]
        pages.append("\n".join(lines))
    return "\n\n".join(pages)

def load_text(filepath: str) -> str:
    return open(filepath, "r").read()

def load_url(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    return response.text[:50000]  # cap to avoid massive pages


# -------------------------------- Strategy 1 --------------------------------
def chunk_fixed(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap  # overlap ensures no hard cuts
    return [c.strip() for c in chunks if c.strip()]
# ----------------------------------------------------------------------------


# -------------------------------- Strategy 2 --------------------------------
def chunk_recursive(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    # Try splitting on paragraph boundaries first
    separators = ["\n\n", "\n", ". ", " "]
    
    def split(text: str, sep_idx: int = 0) -> list[str]:
        if len(text) <= size or sep_idx >= len(separators):
            return [text]
        
        sep = separators[sep_idx]
        parts = text.split(sep)
        chunks, current = [], ""
        
        for part in parts:
            if len(current) + len(part) + len(sep) <= size:
                current += part + sep
            else:
                if current.strip():
                    # current chunk is full — check if it itself needs splitting
                    if len(current) > size:
                        chunks.extend(split(current, sep_idx + 1))
                    else:
                        chunks.append(current.strip())
                current = part + sep
        
        if current.strip():
            chunks.append(current.strip())
        return chunks
    
    raw_chunks = split(text)
    
    # Add overlap: prepend last sentence of previous chunk
    overlapped = []
    for i, chunk in enumerate(raw_chunks):
        if i > 0:
            prev_sentences = raw_chunks[i-1].split(". ")
            overlap_text = ". ".join(prev_sentences[-2:]) + ". "  # last 2 sentences
            chunk = overlap_text + chunk
        overlapped.append(chunk)
    
    return overlapped
# ----------------------------------------------------------------------------


# -------------------------------- Strategy 3 --------------------------------
def chunk_semantic(text: str, threshold: float = 0.3) -> list[str]:
    # Split into sentences first
    sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    if len(sentences) <= 1:
        return sentences
    
    # Embed every sentence
    embeddings = embedder.encode(sentences)
    
    # Find breakpoints where adjacent sentences are dissimilar
    chunks, current_sentences = [], [sentences[0]]
    
    for i in range(1, len(sentences)):
        # Cosine similarity between adjacent sentences
        a, b = embeddings[i-1], embeddings[i]
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        if similarity < threshold:
            # Topic shift detected — start new chunk
            chunks.append(". ".join(current_sentences) + ".")
            current_sentences = [sentences[i]]
        else:
            current_sentences.append(sentences[i])
    
    if current_sentences:
        chunks.append(". ".join(current_sentences) + ".")
    
    return chunks
# ----------------------------------------------------------------------------


# ====================== INGESTION AND RETRIEVAL FUNCTIONS ======================
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

def retrieve_chunks(query: str, collection_name: str, n: int = 3) -> list[dict]:
    col = chroma.get_or_create_collection(collection_name)
    embedding = embedder.encode(query).tolist()
    results = col.query(query_embeddings=[embedding], n_results=n,
                        include=["documents", "metadatas", "distances"])
    return [
        {"text": d, "source": m["source"], "chunk": m["chunk_index"], "distance": dist}
        for d, m, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]


text = load_pdf("../Resources/AI_Policy.pdf")

fixed   = chunk_fixed(text)
recursive = chunk_recursive(text)
semantic  = chunk_semantic(text)

# Ingest with each strategy into separate collections
ingest_chunks(fixed,     "fixed_chunks",     "doc")
ingest_chunks(recursive, "recursive_chunks", "doc")
ingest_chunks(semantic,  "semantic_chunks",  "doc")

# Test questions — write these based on YOUR document
test_cases = [
    {"query": "What penalties does the EU AI Act impose?",      "expected_keyword": "penalty"},
    {"query": "How does the act define high-risk AI systems?",  "expected_keyword": "high-risk"},
    {"query": "What are the transparency requirements?",        "expected_keyword": "transparent"},
    {"query": "Which AI systems are prohibited entirely?",      "expected_keyword": "prohibited"},
    {"query": "What is the enforcement mechanism?",             "expected_keyword": "enforce"},
]

print("\n=== RETRIEVAL QUALITY COMPARISON ===")
for tc in test_cases:
    print(f"\nQ: {tc['query']}")
    for col_name in ["fixed_chunks", "recursive_chunks", "semantic_chunks"]:
        results = retrieve_chunks(tc["query"], col_name, n=3)

        # Check if expected keyword appears in any top-3 result
        hit = any(tc["expected_keyword"].lower() in r["text"].lower() for r in results)
        top_dist = results[0]["distance"] if results else 999
        print(f"  {col_name:20} | hit: {'✓' if hit else '✗'} | top distance: {top_dist:.3f}")



# IMPORTANT NOTE:
# Semantic search gives consistently poor distance results even though it may 
# conduct a hit. It retrieves farther chunks that are semantically related but not
# exact matches. This is due to lesser variability in context of the doc. Since 
# this doc is on AI Policy, many chunks are semantically similar, so the embedding
# model struggles to differentiate them. In contrast, fixed and recursive chunking
# often retrieve the exact chunk containing the keyword, leading to better distance
# scores. In practice, you may want to combine semantic search with keyword filtering
# or hybrid approaches for better accuracy, but for the scope of this project, you
# would use recursive chunking.