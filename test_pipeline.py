import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

import json
with open("Resources/simulations/transcript_9aa25e2a.json") as f:   # Random session_id from a recent run
    data = json.load(f)

similarities = [e["similarity"] for e in data["multi_target_raw"]]
print(f"Count: {len(similarities)}")
print(f"Min: {min(similarities):.3f}, Max: {max(similarities):.3f}")
print(f"Mean: {sum(similarities)/len(similarities):.3f}")

# See the distribution shape
similarities.sort()
print(similarities)