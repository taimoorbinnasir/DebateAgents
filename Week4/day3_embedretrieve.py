import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.ingest import ingest_document
from shared.retrieve import retrieve_chunks

# Ingest once — subsequent runs skip automatically
# ingest_document("../Resources/AI_Policy.pdf", collection_name="eu_ai_act")

# Test 5 queries, print citations alongside retrieved text
queries = [
    "What penalties does the EU AI Act impose?",
    "How does the act define high-risk AI systems?",
    "Which AI systems are prohibited entirely?",
    "What are the transparency requirements?",
    "What is the enforcement mechanism?",
]

print("\n=== RETRIEVAL WITH CITATIONS ===")
for q in queries:
    print(f"\nQ: {q}")
    results = retrieve_chunks(q, "eu_ai_act", n=3)
    
    for i, r in enumerate(results):
        print(f"  [{i+1}] distance={r['distance']:.3f} | {r['citation']}")
        print(f"       {r['text'][:150]}...")
    
    # Flag weak retrievals
    if all(r["distance"] > 0.8 for r in results):
        print("  ⚠️  All distances > 0.8 — answer may not be in document")


# Chromadb retrieval is deterministic — same query always returns same chunks
q = "What penalties does the EU AI Act impose?"

runs = [retrieve_chunks(q, "eu_ai_act", n=3) for _ in range(3)]
ids = [[r["chunk_index"] for r in run] for run in runs]

print("Consistent:", all(x == ids[0] for x in ids))