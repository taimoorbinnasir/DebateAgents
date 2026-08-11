import os, sys, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
from datetime import datetime
from .memory import embedder
from .tools import llm
from .retrieve import retrieve_agent_sources
from .agents import AGENTS


# LLM answer response
def agent_respond_streaming(agent_id: str, shared_history: list, round_num: int) -> str:
    config = AGENTS[agent_id]
    sources = retrieve_agent_sources(agent_id, shared_history[-1] if shared_history else "", n=2)
    
    source_context = "\n".join([
        f"[{r['citation']}]: {r['text'][:200]}"
        for r in sources
    ]) if sources else ""
    
    conversation = "\n".join(shared_history[-10:])
    prompt = f"""{config['system']}

{"Relevant sources you found:" + chr(10) + source_context if source_context else ""}

Current conversation:
{conversation}

Respond as {config['name']} in 3-5 sentences. Be direct and in character."""

    # Stream output token by token
    print(f"\n{config['name']} ({config['stance']}): ", end="", flush=True)
    full_response = ""
    for chunk in llm.stream(prompt):
        token = chunk.content
        print(token, end="", flush=True)
        full_response += token
    print()  # newline after response
    
    return full_response



# Save resources by each agent in relevant files
def save_agent_resources(agent_id: str, topic: str, results: list[dict]):
    """Save raw search results to ../Resources/<agent_id>/"""
    agent_name = AGENTS[agent_id]["name"]
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resource_dir = os.path.join(project_root, "Resources", agent_name)
    os.makedirs(resource_dir, exist_ok=True)
    print(f"Saving to: {os.path.abspath(resource_dir)}")  # add this
    
    # Save each source as a separate file
    for i, r in enumerate(results):
        filename = f"{r['title'][:50].replace('/', '_')}.json"
        filepath = os.path.join(resource_dir, filename)

        with open(filepath, "w") as f:
            json.dump({
                "agent": agent_name,
                "topic": topic,
                "title": r["title"],
                "url": r["link"],
                "content": r["snippet"],
                "fetched_at": str(datetime.now())
            }, f, indent=2)
    
    # Save a manifest
    manifest_path = os.path.join(resource_dir, "_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump({
            "agent": agent_name,
            "topic": topic,
            "sources": [r["title"] for r in results],
            "ingested_at": str(datetime.now())
        }, f, indent=2)
    
    print(f"  {agent_name}: resources saved to {resource_dir}")


# Stopping condition
def should_stop(shared_history: list, round_num: int, max_rounds: int = 10) -> tuple[bool, str]:
    """Returns (should_stop, reason)"""
    
    # Hard limit — always stops
    if round_num >= max_rounds:
        return True, f"Maximum rounds ({max_rounds}) reached"
    
    # Repetition detection — stops if last 2 rounds are too similar
    if round_num >= 4:
        recent = shared_history[-12:]  # last 2 full rounds (6 agents x 2)
        earlier = shared_history[-24:-12]
        if recent and earlier:
            recent_text = " ".join(recent)
            earlier_text = " ".join(earlier)

            r_emb = embedder.encode(recent_text)
            e_emb = embedder.encode(earlier_text)
            similarity = np.dot(r_emb, e_emb) / (np.linalg.norm(r_emb) * np.linalg.norm(e_emb))
            if similarity > 0.92:  # very similar — agents repeating themselves
                return True, "Conversation has converged — agents repeating arguments"
    
    # Escalation ceiling — stops if hardliners are too extreme
    if round_num >= 3:
        last_round = shared_history[-6:]
        escalation_check = llm.invoke(
            f"Rate the overall hostility of this conversation excerpt from 1-10. "
            f"Return only a number.\n{''.join(last_round)}"
        )
        try:
            hostility = int(escalation_check.content.strip())
            if hostility >= 9:
                return True, f"Hostility ceiling reached (score: {hostility}/10)"
        except:
            pass
    
    return False, ""




# Final report on completion of the debate
def conclude_simulation(shared_history: list, extremity_log: dict, stop_reason: str) -> str:
    transcript = "\n".join(shared_history)
    
    report = llm.invoke(f"""Analyze this debate and write a structured report.

Stop reason: {stop_reason}

Answer each section:
## 1. Position Drift
Did any agent shift their position? Who moved most, who was immovable?

## 2. Influence Map  
Which agent had the most impact on the conversation's direction?

## 3. Radicalization
Did any agent become more extreme over time? What triggered it?

## 4. Fault Lines
What was the core unresolvable disagreement?

## 5. Verdict
If forced to summarize who "won" the argument on evidence quality alone, who was it?

Transcript:
{transcript}""")
    
    # Save report
    report_path = os.path.expanduser(f"~/Resources/simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(report_path, "w") as f:
        f.write(f"# Debate Simulation Report\n")
        f.write(f"**Stop reason:** {stop_reason}\n\n")
        f.write(report.content)
    
    print(f"\n📊 Report saved to {report_path}")
    return report.content


# def run_simulation(topic: str, max_rounds: int = 10):
#     shared_history = [f"TOPIC: {topic}"]
#     extremity_log = {agent_id: [] for agent_id in AGENTS}
#     agent_ids = list(AGENTS.keys())
    
#     print(f"\n{'='*60}")
#     print(f"DEBATE: {topic}")
#     print(f"{'='*60}")
    
#     # Web RAG — search once at start
#     print("\n🔍 Agents searching for sources...")
#     for agent_id in agent_ids:
#         ingest_agent_sources(agent_id, topic)
    
#     # Simulation loop
#     for round_num in range(1, max_rounds + 1):
#         print(f"\n{'─'*60}")
#         print(f"ROUND {round_num}")
#         print(f"{'─'*60}")
        
#         random.shuffle(agent_ids)
        
#         for agent_id in agent_ids:
#             response = agent_respond_streaming(agent_id, shared_history, round_num)
#             statement = f"{AGENTS[agent_id]['name']}: {response}"
#             shared_history.append(statement)
#             store_agent_statement(agent_id, response, round_num)
            
#             # Track extremity
#             score = score_extremity(agent_id, response)
#             extremity_log[agent_id].append(score)
        
#         # Check stopping conditions after each round
#         stop, reason = should_stop(shared_history, round_num, max_rounds)
#         if stop:
#             print(f"\n🛑 Stopping: {reason}")
#             break
    
#     # Generate conclusion
#     print(f"\n{'='*60}")
#     print("GENERATING ANALYSIS REPORT...")
#     print(f"{'='*60}")
#     conclude_simulation(shared_history, extremity_log, reason)