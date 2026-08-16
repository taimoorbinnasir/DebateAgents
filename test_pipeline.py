import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Week5.DebateAgents import agent_respond
from shared.agents import AGENT_PARAMS, build_system_prompt
from shared.config import topic_key
from shared.ingest import ingest_agent_sources, topic_key
from shared.memory import store_agent_statement, recall_agent_history
from shared.retrieve import retrieve_agent_sources

TOPIC = "AI regulation"
SESSION_ID = "test_session_001"

def assert_true(condition: bool, msg: str = ""):
    if not condition:
        raise AssertionError(msg or "Assertion failed")

def test(name: str, fn):
    try:
        fn()
        print(f"  ✅ {name}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")

print("\n=== 1. AGENT CONFIG ===")
test("AGENT_PARAMS loads",        lambda: assert_true(len(AGENT_PARAMS) == 6))
test("All agents have name",      lambda: [assert_true("name" in v) for v in AGENT_PARAMS.values()])
test("All agents have stance",    lambda: [assert_true("stance" in v) for v in AGENT_PARAMS.values()])
test("build_system_prompt works", lambda: assert_true(len(build_system_prompt("pro_hardliner")) > 100))

print("\n=== 2. TOPIC KEY ===")
test("Same topic → same key",     lambda: assert_true(topic_key(TOPIC) == topic_key(TOPIC)))
test("Different topic → diff key",lambda: assert_true(topic_key(TOPIC) != topic_key("climate change")))
test("Case insensitive",          lambda: assert_true(topic_key("AI Regulation") == topic_key("ai regulation")))

print("\n=== 3. MEMORY ===")
test("Store statement",           lambda: store_agent_statement("pro_hardliner", "Test statement about AI.", 1, SESSION_ID))
test("Recall statement",          lambda: assert_true(len(recall_agent_history("pro_hardliner", "AI", SESSION_ID, n=1)) > 0))
test("Different session isolated",lambda: assert_true(len(recall_agent_history("pro_hardliner", "AI", "other_session", n=1)) == 0))

print("\n=== 4. WEB RAG ===")
test("Ingest sources",            lambda: ingest_agent_sources("pro_hardliner", TOPIC, SESSION_ID))
test("Retrieve sources",          lambda: assert_true(isinstance(retrieve_agent_sources("pro_hardliner", "AI risks", TOPIC, n=2), list)))
test("Same topic reuses cache",   lambda: ingest_agent_sources("pro_hardliner", TOPIC, "different_session"))  # should print "already ingested"

print("\n=== 5. SINGLE AGENT RESPONSE ===")
def test_agent_respond():
    test_topic = "AI regulation"
    test_session = "test_session_001"
    shared_history = [f"TOPIC: {test_topic}", "Aggro: AI must be regulated immediately."]
    reply = agent_respond("con_hardliner", shared_history, round_num=1, session_id=test_session)
    assert len(reply) > 20, "Reply too short"
    assert "MODERATOR" not in reply, "Agent acting as moderator"

test("Agent responds in character", test_agent_respond)
print("\n=== DONE ===\n")