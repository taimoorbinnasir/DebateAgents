#  ================================================================================
# ||                  UNDERSTANDING THIS PART STILL LEFT                          ||
#  ================================================================================
import sys, os, random
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.agents import AGENTS
from shared.memory import store_agent_statement, recall_agent_history
from shared.web_rag import ingest_agent_sources, retrieve_agent_sources
from shared.tools import llm
import numpy as np

# ===================== AGENT RESPONSE =====================

def agent_respond(agent_id: str, shared_history: list, round_num: int) -> str:
    config = AGENTS[agent_id]
    
    # 1. Recall own past statements (private memory)
    last_message = shared_history[-1] if len(shared_history) > 1 else ""
    past = recall_agent_history(agent_id, last_message, n=2)
    past_text = "\n".join(past) if past else "This is your first statement."
    
    # 2. Retrieve relevant sources (web RAG)
    sources = retrieve_agent_sources(agent_id, last_message, n=2)
    source_text = "\n".join([
        f"[{r['source_title']}]: {r['text'][:200]}"
        for r in sources
    ]) if sources else ""
    
    # 3. Build conversation context (shared memory — last 10 messages)
    conversation = "\n".join(shared_history[-10:])
    
    # 4. Build full prompt
    prompt = f"""{config['system']}

Your past statements — stay consistent with these:
{past_text}

{"Relevant sources you found — cite these naturally when relevant:" + chr(10) + source_text if source_text else ""}

Current conversation:
{conversation}

Respond as {config['name']} in 3-5 sentences. Be direct and in character."""

    # 5. Stream response token by token
    print(f"\n{config['name']} ({config['stance'].upper()}): ", end="", flush=True)
    full_response = ""
    for chunk in llm.stream(prompt):
        token = chunk.content
        print(token, end="", flush=True)
        full_response += token
    print()
    
    return full_response


# ===================== STOPPING CONDITIONS =====================

def score_extremity(agent_id: str, statement: str) -> int:
    """Rate how extreme a statement is on 1-10."""
    response = llm.invoke(
        f"Rate the extremity/hostility of this statement from 1 (very moderate) "
        f"to 10 (very extreme). Return only a number.\nStatement: {statement}"
    )
    try:
        return int(response.content.strip())
    except:
        return 5

def should_stop(shared_history: list, round_num: int, max_rounds: int) -> tuple[bool, str]:
    # Hard limit
    if round_num >= max_rounds:
        return True, f"Maximum rounds ({max_rounds}) reached"
    
    # Repetition detection — kicks in after round 4
    if round_num >= 4:
        msgs_per_round = len(AGENTS)
        recent  = shared_history[-(msgs_per_round * 2):]
        earlier = shared_history[-(msgs_per_round * 4):-(msgs_per_round * 2)]
        
        if recent and earlier:
            from shared.memory import embedder
            r_emb = embedder.encode(" ".join(recent))
            e_emb = embedder.encode(" ".join(earlier))
            similarity = np.dot(r_emb, e_emb) / (
                np.linalg.norm(r_emb) * np.linalg.norm(e_emb)
            )
            if similarity > 0.92:
                return True, f"Conversation converged (similarity: {similarity:.2f})"
    
    return False, ""


# ===================== CONCLUSION =====================

def conclude_simulation(topic: str, shared_history: list, 
                        extremity_log: dict, stop_reason: str):
    transcript = "\n".join(shared_history)
    
    # Format extremity scores
    scores_text = "\n".join([
        f"{AGENTS[aid]['name']}: {scores}"
        for aid, scores in extremity_log.items()
    ])
    
    print(f"\n{'='*60}")
    print("GENERATING ANALYSIS REPORT...")
    print(f"{'='*60}\n")
    
    report = llm.invoke(f"""Analyze this debate transcript and write a structured report.

Topic: {topic}
Stop reason: {stop_reason}
Extremity scores per agent per round (1=moderate, 10=extreme):
{scores_text}

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
Who argued most effectively on evidence quality alone?

Transcript:
{transcript}""")
    
    # Save transcript + report
    from datetime import datetime
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "Resources", "simulations")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Transcript JSON
    import json
    transcript_path = os.path.join(output_dir, f"transcript_{timestamp}.json")
    with open(transcript_path, "w") as f:
        json.dump({
            "topic": topic,
            "stop_reason": stop_reason,
            "extremity_log": extremity_log,
            "transcript": shared_history
        }, f, indent=2)
    
    # Analysis report markdown
    report_path = os.path.join(output_dir, f"report_{timestamp}.md")
    with open(report_path, "w") as f:
        f.write(f"# Debate Simulation Report\n")
        f.write(f"**Topic:** {topic}\n")
        f.write(f"**Stop reason:** {stop_reason}\n\n")
        f.write(report.content)
    
    print(report.content)
    print(f"\n📄 Transcript saved: {transcript_path}")
    print(f"📊 Report saved:     {report_path}")


# ===================== MAIN SIMULATION LOOP =====================

def run_simulation(topic: str, max_rounds: int = 10):
    shared_history = [f"TOPIC: {topic}"]
    extremity_log = {agent_id: [] for agent_id in AGENTS}
    agent_ids = list(AGENTS.keys())
    stop_reason = f"Maximum rounds ({max_rounds}) reached"
    
    print(f"\n{'='*60}")
    print(f"DEBATE SIMULATION")
    print(f"Topic: {topic}")
    print(f"Agents: {', '.join([AGENTS[a]['name'] for a in agent_ids])}")
    print(f"{'='*60}")
    
    # Web RAG — each agent searches once at start
    print("\n🔍 Agents searching for sources...")
    for agent_id in agent_ids:
        ingest_agent_sources(agent_id, topic)
    print("✓ Sources ingested\n")
    
    # Main loop
    for round_num in range(1, max_rounds + 1):
        print(f"\n{'─'*60}")
        print(f"ROUND {round_num}/{max_rounds}")
        print(f"{'─'*60}")
        
        random.shuffle(agent_ids)  # random order each round
        
        for agent_id in agent_ids:
            # Generate response
            response = agent_respond(agent_id, shared_history, round_num)
            
            # Append to shared history
            statement = f"{AGENTS[agent_id]['name']}: {response}"
            shared_history.append(statement)
            
            # Store in private memory
            store_agent_statement(agent_id, response, round_num)
            
            # Track extremity
            score = score_extremity(agent_id, response)
            extremity_log[agent_id].append(score)
            print(f"  [extremity: {score}/10]")
        
        # Check stopping conditions
        stop, reason = should_stop(shared_history, round_num, max_rounds)
        if stop:
            stop_reason = reason
            print(f"\n🛑 {stop_reason}")
            break
    
    # Conclude
    conclude_simulation(topic, shared_history, extremity_log, stop_reason)


# ===================== ENTRY POINT =====================

if __name__ == "__main__":
    topic = input("Enter debate topic: ").strip()
    if not topic:
        topic = "AI regulation"
    
    max_rounds = input("Max rounds (default 10): ").strip()
    max_rounds = int(max_rounds) if max_rounds.isdigit() else 10
    
    run_simulation(topic, max_rounds)