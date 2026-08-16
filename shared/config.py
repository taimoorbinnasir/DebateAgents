import hashlib

# Basic
MODEL = "claude-haiku-4-5"
MAX_TOKENS = 500
MEMORY_DB_PATH = "./memory_db"
COLLECTION_NAME = "agent_memory"

# Pricing for cost tracking
INPUT_COST_PER_M = 0.8
OUTPUT_COST_PER_M = 4.0

# Debate sim settings (you'll use these in Week 5)
NUM_ROUNDS = 10
NUM_PRO_AGENTS = 3
NUM_CON_AGENTS = 3


def topic_key(topic: str) -> str:
    return hashlib.md5(topic.lower().strip().encode()).hexdigest()[:8]