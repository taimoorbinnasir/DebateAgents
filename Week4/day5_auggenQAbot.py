import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.tools import llm
from shared.ingest import ingest_document
from shared.retrieve import retrieve_chunks
from langchain_core.messages import HumanMessage, AIMessage

COLLECTION = "eu_ai_act"
DISTANCE_THRESHOLD = 0.7

def build_context(query: str) -> tuple[str, list[str]]:
    """Retrieve chunks and format as context + citation list."""
    results = retrieve_chunks(query, COLLECTION, n=3)
    strong = [r for r in results if r["distance"] < DISTANCE_THRESHOLD]

    # If no strong results (all >= 0.8), return a message indicating no relevant information
    if not strong:
        return "No relevant information found in the document.", []
    
    context = "\n\n".join([
        f"[Source: {r['citation']}]\n{r['text']}"
        for r in strong
    ])
    citations = [r["citation"] for r in strong]
    return context, citations


def ask(query: str, chat_history: list) -> tuple[str, list[str]]:
    """Single turn: retrieve → augment → generate."""
    context, citations = build_context(query)

    # Uses the last 3 turns of chat history to provide context for the LLM,
    # but not the entire history to save tokens
    history_text = "\n".join([
        f"Human: {m.content}" if isinstance(m, HumanMessage) else f"AI: {m.content}"
        for m in chat_history[-6:]  # last 3 turns only — saves tokens
    ])
    
    response = llm.invoke(f"""You are a helpful assistant answering questions about the EU AI Act.
Answer using ONLY the context provided. Do NOT use any outside knowledge. Do NOT infer or extrapolate.
If the context only mentions the topic briefly, say:
"The document only briefly mentions this: [quote the relevant text directly]"
If the context doesn't answer the question, say:
"This specific information is not in the document."
End every answer with: "Sources:\n[1] <citation1>\n[2] <citation2>..." (list all sources you used).

Context:
{context}

{"Previous conversation:" + chr(10) + history_text if history_text else ""}

Question: {query}""")
    
    return response.content, citations


def run_qa_bot():
    # Ingest once
    ingest_document("../Resources/AI_Policy.pdf", COLLECTION)
    ingest_document("../Resources/CBC_AI_Policy.pdf", COLLECTION)
    
    chat_history = []
    print("\n📄 EU AI Act Q&A fed on AI_Policy.pdf (type 'exit' to quit, 'history' to see chat)\n")
    
    while True:
        query = input("You: ").strip()
        if not query:
            continue

        if query.lower() == "exit" or query.lower() == "e":
            break

        if query.lower() == "history":
            for m in chat_history:
                prefix = "You:" if isinstance(m, HumanMessage) else "AI:"
                print(f"{prefix} {m.content[:100]}...")
            continue
        
        answer, citations = ask(query, chat_history)
        
        # Update buffer memory
        chat_history.append(HumanMessage(content=query))
        chat_history.append(AIMessage(content=answer))
        
        print(f"\nAssistant: {answer}\n")


run_qa_bot()