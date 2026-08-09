import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.load_doc import load_pdf
from shared.chunker import chunk_fixed, chunk_recursive, chunk_semantic
from shared.ingest import ingest_chunks
from shared.retrieve import retrieve_chunks


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