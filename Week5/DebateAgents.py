import sys, os, random, uuid
import queue as q
from anthropic import Anthropic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.agents import AGENT_PARAMS, build_system_prompt, moderator_summary
from shared.memory import store_agent_statement, recall_agent_history
from shared.ingest import ingest_agent_sources
from shared.retrieve import retrieve_agent_sources

from .helpers import get_last_ally_statement, get_last_opponent_statement, clean_history, should_stop
from .eval import score_extremity, conclude_simulation


# ===================== AGENT RESPONSE =====================
def agent_respond(agent_id: str, shared_history: list, round_num: int, session_id: str) -> str:
    topic = shared_history[0].replace("TOPIC: ", "").strip()
    agent_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    p = AGENT_PARAMS[agent_id]

    last_message = shared_history[-1] if len(shared_history) > 1 else ""
    past    = recall_agent_history(agent_id, last_message, session_id, n=2)
    sources = retrieve_agent_sources(agent_id, last_message, topic, n=2)
    last_opponent = get_last_opponent_statement(agent_id, shared_history)
    last_ally     = get_last_ally_statement(agent_id, shared_history)
    debate_lines  = clean_history(shared_history)

    # Build user content
    sections = [f"Current debate on: {shared_history[0]}\n"]

    if past:
        sections.append("Your past statements (stay consistent):\n" + "\n".join(past))

    if sources:
        cited = "\n".join([f"[{r['source_title']}]: {r['text'][:200]}" for r in sources])
        sections.append(f"Relevant sources (cite naturally if applicable):\n{cited}")

    if last_ally:
        sections.append(f"Your ally's recent point:\n{last_ally}")

    sections.append(
        f"Opponent's most recent argument to address:\n"
        f"{last_opponent if last_opponent else 'No opponent statement yet — open the debate.'}"
    )

    sections.append("Recent conversation:\n" + "\n".join(debate_lines[-8:]))
    sections.append(f"Respond as {p['name']} in 3-5 sentences. Address the opponent's argument directly.")

    user_content = "\n\n".join(sections)

    response = agent_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=build_system_prompt(agent_id),
        messages=[{"role": "user", "content": user_content}]
    )

    reply = response.content[0].text

    # Word-by-word print to simulate streaming
    print(f"\n{p['name']} ({p['stance'].upper()}): ", end="", flush=True)
    for word in reply.split():
        print(word + " ", end="", flush=True)
    print()

    store_agent_statement(agent_id, reply, round_num, session_id)
    return reply


# ===================== MAIN SIMULATION LOOP =====================
def run_simulation(topic: str, max_rounds: int = 10):
    session_id = str(uuid.uuid4())[:8]
    shared_history = [f"TOPIC: {topic}"]
    extremity_log  = {agent_id: [] for agent_id in AGENT_PARAMS}
    stop_reason    = f"Maximum rounds ({max_rounds}) reached"

    pro_agents = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "pro"]
    con_agents = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "con"]

    print(f"\n{'='*60}\nDEBATE: {topic}\nAgents: {', '.join([AGENT_PARAMS[a]['name'] for a in AGENT_PARAMS])}\n{'='*60}")

    # Web RAG — each agent searches once
    print("\n🔍 Agents searching for sources...")
    for agent_id in AGENT_PARAMS:
        ingest_agent_sources(agent_id, topic, session_id)
    print("✓ Sources ingested\n")

    # Pass session_id to agent_respond
    for agent_id in turn_order:
        reply = agent_respond(agent_id, shared_history, round_num, session_id)

    for round_num in range(1, max_rounds + 1):
        print(f"\n{'─'*60}\nROUND {round_num}/{max_rounds}\n{'─'*60}")

        # Interleaved pro/con turn order
        random.shuffle(pro_agents)
        random.shuffle(con_agents)
        turn_order = []
        for p, c in zip(pro_agents, con_agents):
            turn_order.append(p)
            turn_order.append(c)

        for agent_id in turn_order:
            reply     = agent_respond(agent_id, shared_history, round_num)
            statement = f"{AGENT_PARAMS[agent_id]['name']}: {reply}"
            shared_history.append(statement)
            store_agent_statement(agent_id, reply, round_num)
            score = score_extremity(agent_id, reply)
            extremity_log[agent_id].append(score)
            print(f"  [extremity: {score}/10]")

        # Moderator evaluates after each round
        mod_summary = moderator_summary(shared_history, round_num)
        shared_history.append(f"MODERATOR: {mod_summary}")

        stop, reason = should_stop(shared_history, round_num, max_rounds)
        if stop:
            stop_reason = reason
            print(f"\n🛑 {stop_reason}")
            break

    conclude_simulation(topic, shared_history, extremity_log, stop_reason)


# ===================== SIMULATION LOOP FOR BACKEND =====================
# Simulation loop that pushes events to a queue instead of printing
def run_simulation_streamed(topic: str, max_rounds: int, session_id: str, event_queue=None):
    # If no queue provided, fall back to print behavior
    def push(event: dict):
        if event_queue:
            from backend.manager import push_event
            push_event(session_id, event)
        else:
            print(event)  # fallback for terminal runs

    # Push research phase start
    push({"type": "research_start", "total_agents": len(AGENT_PARAMS)})
    
    shared_history = [f"TOPIC: {topic}"]
    extremity_log  = {agent_id: [] for agent_id in AGENT_PARAMS}
    stop_reason    = f"Maximum rounds ({max_rounds}) reached"
    pro_agents     = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "pro"]
    con_agents     = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "con"]

    # Ingest sources
    for i, agent_id in enumerate(AGENT_PARAMS):
        ingest_agent_sources(agent_id, topic, session_id)
        push({
            "type": "research_progress",
            "completed": i + 1,
            "total": len(AGENT_PARAMS),
            "agent_name": AGENT_PARAMS[agent_id]["name"]
        })
    
    push({"type": "research_complete"})

    for round_num in range(1, max_rounds + 1):
        push({"type": "round_start", "round": round_num, "max_rounds": max_rounds})
        
        random.shuffle(pro_agents)
        random.shuffle(con_agents)
        turn_order = [x for pair in zip(pro_agents, con_agents) for x in pair]

        for agent_id in turn_order:
            reply = agent_respond(agent_id, shared_history, round_num, session_id)
            statement = f"{AGENT_PARAMS[agent_id]['name']}: {reply}"
            shared_history.append(statement)
            store_agent_statement(agent_id, reply, round_num, session_id)
            score = score_extremity(agent_id, reply)
            extremity_log[agent_id].append(score)

            # Push agent statement event
            push({
                "type":       "agent_statement",
                "agent_id":   agent_id,
                "agent_name": AGENT_PARAMS[agent_id]["name"],
                "stance":     AGENT_PARAMS[agent_id]["stance"],
                "round_num":  round_num,
                "text":       reply,
                "extremity":  score
            })

        # Moderator after each round
        mod_text = moderator_summary(shared_history, round_num)
        shared_history.append(f"MODERATOR: {mod_text}")
        push({"type": "moderator_summary", "round": round_num, "text": mod_text})

        push({"type": "round_end", "round": round_num})

        stop, reason = should_stop(shared_history, round_num, max_rounds)
        if stop:
            stop_reason = reason
            break

    conclude_simulation(topic, shared_history, extremity_log, stop_reason)
    push({"type": "simulation_complete", "stop_reason": stop_reason})


# ===================== ENTRY POINT =====================
if __name__ == "__main__":
    topic      = input("Enter debate topic: ").strip() or "AI regulation"
    max_rounds = input("Max rounds (default 3 for testing): ").strip()
    max_rounds = int(max_rounds) if max_rounds.isdigit() else 3
    run_simulation(topic, max_rounds)