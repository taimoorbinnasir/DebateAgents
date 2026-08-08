import sys, os, json, re
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.tools import llm, tools
from shared.memory import remember, recall, collection

from datetime import datetime
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage


# ===================== MEMORY INJECTION =====================
def get_all_facts(n: int = 10) -> list[str]:
    """Retrieve all stored facts regardless of query."""
    results = collection.get()
    return results["documents"] if results["documents"] else []

def build_prompt(query: str) -> ChatPromptTemplate:
    # Use broad retrieval + query-specific retrieval combined
    all_facts = get_all_facts()
    query_facts = recall(query, n=3)
    
    # Combine and deduplicate
    combined = list(dict.fromkeys(all_facts + query_facts))
    facts_text = "\n".join(f"- {f}" for f in combined) if combined else "No prior facts known."
    
    return ChatPromptTemplate.from_messages([
        ("system", f"""You are a helpful personal assistant with memory of past sessions.

What you remember about the user:
{facts_text}

Use this context naturally. If asked what you know, list these facts explicitly."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])


# ===================== FACT EXTRACTION =====================
def extract_and_store_facts(chat_history: list):
    if not chat_history:
        return
    
    history_text = "\n".join([
        f"Human: {m.content}" if isinstance(m, HumanMessage) else f"AI: {m.content}"
        for m in chat_history
    ])
    
    response = llm.invoke(
        f"""Extract factual, reusable information about the user from this conversation.
Only extract concrete facts: preferences, goals, background, decisions made.
Ignore small talk. Return as a JSON list of strings. Return [] if nothing worth storing.
Return ONLY the JSON list, no markdown, no backticks, no other text.

Conversation:
{history_text}"""
    )
    
    try:
        # Strip markdown code fences if present
        raw = response.content.strip()
        raw = re.sub(r"```(?:json)?\n?", "", raw).strip()
        
        facts = json.loads(raw)
        for i, fact in enumerate(facts):
            fact_id = f"fact_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
            remember(fact, fact_id, metadata={"source": "conversation", "timestamp": str(datetime.now())})
            print(f"  💾 Stored: {fact}")
    except json.JSONDecodeError as e:
        print(f"  ⚠️ Could not parse facts: {e}")
        print(f"  Raw response: {response.content}")  # add this to debug future failures


# ===================== MAIN SESSION LOOP =====================
def run_session():
    chat_history = []
    print("\n🤖 Personal Assistant (type 'exit' to end session)\n")
    
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        
        # Fresh retrieval + prompt rebuild each turn
        prompt = build_prompt(user_input)
        agent = create_tool_calling_agent(llm, tools, prompt)
        executer = AgentExecutor(agent=agent, tools=tools, verbose=False)
        
        result = executer.invoke({
            "input": user_input,
            "chat_history": chat_history
        })
        
        answer = result["output"]
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=answer))
        
        print(f"\nAssistant: {answer}\n")
    
    # End of session — extract and store facts
    print("\n--- Session ended. Extracting memorable facts... ---")
    extract_and_store_facts(chat_history)
    print("--- Facts stored. See you next session! ---\n")



# SESSION 1
# You: I have a friend named Bilal and he's a BS Biology student studying Master's in Genomics
# You: He finds some parts of the course challenging and doesn't know what to do
# You: He likes concise explanations, though also requires verbose explanations when needed
# You: exit


# SESSION 2
# You: Do you remember anything about me?
# You: What am I building?
# You: exit

# It should recall your name, project, and preferences without you re-stating them.

run_session()
print(collection.get())

# Check whether extract_and_store_facts pulled the right things — it sometimes stores
# redundant or vague facts. That's expected and is the same problem your debate agents
# will face: deciding what's worth remembering vs noise. You'll tune the extraction
# prompt for that in Week 5.
