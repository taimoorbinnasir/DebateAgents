#  ==============================================================================
# ||  This section remembers a series of facts about a user and retrieves them  ||
# || later, even across process restarts, using ChromaDB for persistent storage ||
#  ==============================================================================
import sys, os, chromadb
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.tools import llm, tools
from shared.memory import remember, recall

from datetime import datetime
from sentence_transformers import SentenceTransformer
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

# Runs locally, no API key, free
embedder = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim, fast, good enough

# PersistentClient saves to disk — survives process restarts
chroma = chromadb.PersistentClient(path="./memory_db")
collection = chroma.get_or_create_collection("agent_memory")


# ----------------------------- FUNCTION DEFINITIONS -----------------------------
# Builds a prompt that includes relevant facts for the current query
def build_prompt_with_memory(query: str) -> ChatPromptTemplate:
    relevant_facts = recall(query, n=3)
    facts_text = "\n".join(f"- {f}" for f in relevant_facts)
    
    return ChatPromptTemplate.from_messages([
        ("system", f"""You are a helpful personal assistant.
        
Here is what you know about the user:
{facts_text}

Use this context naturally when relevant. Don't explicitly say 'I know that you...' unless asked."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])


# Asks a question with memory retrieval, returning the agent's answer
def ask_with_memory(query: str, chat_history: list) -> str:
    prompt = build_prompt_with_memory(query)
    agent = create_tool_calling_agent(llm, tools, prompt)
    executer = AgentExecutor(agent=agent, tools=tools, verbose=False)
    result = executer.invoke({"input": query, "chat_history": chat_history})
    return result["output"]
# --------------------------------------------------------------------------------




#  ==========================================================
# ||    THIS SECTION WAS JUST TO TEST THE CHROMADB SETUP    ||
#  ==========================================================
# Store facts
# remember("Ahmed prefers Python over JavaScript", "pref_001")
# remember("Ahmed is studying LLM agents and multi-agent systems", "study_001")
# remember("Ahmed wants to build a debate simulation with 6 agents", "goal_001")
# remember("Ahmed is using Claude Haiku for cost efficiency", "tool_001")
# remember("Ahmed finds LangChain unstable and prefers raw Anthropic SDK", "tool_002")
# remember("Ahmed is a CS student about to graduate", "bio_001")


# Retrieves a list of relevant facts for a given query
# queries = [
#     "What programming language should I recommend?",
#     "What is this person building?",
#     "What tools does this person prefer?",
#     "Tell me about this person's background"
# ]

# for q in queries:
#     facts = recall(q, n=2)
#     print(f"\nQuery: {q}")
#     print(f"Retrieved: {facts}")


# ------------------- CHECKING FACT RECOLLECTION ACROSS SESSIONS -------------------
# SESSION 1 — store facts, have a conversation
print("=== SESSION 1 ===")
chat_history = []

remember("User's name is Ahmed", "name_001")
remember("Ahmed dislikes verbose explanations, prefers concise answers", "pref_002")
remember("Ahmed is currently on Week 3 of his LLM learning roadmap", "progress_001")

questions_s1 = [
    "What should I focus on this week in my learning?",
    "Recommend a project idea that fits my current level.",
]

for q in questions_s1:
    answer = ask_with_memory(q, chat_history)
    chat_history.append(HumanMessage(content=q))
    chat_history.append(AIMessage(content=answer))
    print(f"Q: {q}\nA: {answer}\n")

print("\n--- Simulating process restart ---\n")


# SESSION 2 — fresh process, no chat_history, but ChromaDB persists
print("=== SESSION 2 ===")
chat_history = []  # wiped — simulates restart

questions_s2 = [
    "Do you know anything about me?",  # should recall stored facts
    "What was I working on?",          # should retrieve progress fact
]

for q in questions_s2:
    answer = ask_with_memory(q, chat_history)
    chat_history.append(HumanMessage(content=q))
    chat_history.append(AIMessage(content=answer))
    print(f"Q: {q}\nA: {answer}\n")
# --------------------------------------------------------------------------------



#  =================================================================================
# || This metadata filtering is exactly how each debate agent will recall only its ||
# ||   own past statements or only what specific opponents said — the dual memory  ||
# ||            structure (shared + private) you'll need in Week 5                 ||
#  =================================================================================

# Store facts with agent-specific metadata
remember(
    "Agent_1 argued that AI regulation stifles innovation",
    fact_id="agent1_round1",
    metadata={"agent": "Agent_1", "round": 1, "stance": "pro", "timestamp": str(datetime.now())}
)

# Retrieve only facts from a specific agent
def recall_for_agent(query: str, agent_name: str, n: int = 3) -> list[str]:
    embedding = embedder.encode(query).tolist()
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n,
        where={"agent": agent_name}  # filter by metadata
    )
    return results["documents"][0] if results["documents"][0] else []