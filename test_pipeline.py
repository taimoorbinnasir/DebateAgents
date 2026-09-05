import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from shared.agents import AGENT_PARAMS
from shared.ingest import ingest_agent_sources
from shared.retrieve import retrieve_agent_sources

# A brand-new topic with no prior ingestion — forces a real end-to-end test of
# ingest -> embed -> store -> retrieve, instead of replaying an
# already-ingested collection.
TOPIC = "pineapple on pizza: does it belong?"

QUERIES = {
    "topic string":           TOPIC,
    "rhetorical rebuttal":    "Isn't pineapple just a gimmick that ruins a good pizza?",
    "empty (round-1 opener)": "",
}

print(f"Ingesting fresh sources for topic: {TOPIC!r}\n")
for agent_id in AGENT_PARAMS:
    ingest_agent_sources(agent_id, TOPIC)

for agent_id in AGENT_PARAMS:
    agent_name = AGENT_PARAMS[agent_id]["name"]
    print(f"\n{'='*70}\nAGENT: {agent_id} ({agent_name})\n{'='*70}")

    for label, query in QUERIES.items():
        print(f"\n--- query [{label}]: {query!r}")
        results = retrieve_agent_sources(agent_id, query, TOPIC, n=3)

        if not results:
            print("  -> 0 sources passed the distance filter")
        else:
            for r in results:
                print(f"  -> PASSED dist={r['distance']:.4f} [{r['source_title']}] {r['text'][:80]!r}")

print("\nDone")
