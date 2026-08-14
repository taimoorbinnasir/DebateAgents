import sys, os, random, json
import numpy as np
from datetime import datetime
from anthropic import Anthropic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.agents import AGENT_PARAMS, build_system_prompt
from shared.memory import embedder, store_agent_statement, recall_agent_history
from shared.tools import llm
from shared.ingest import ingest_agent_sources
from shared.retrieve import retrieve_agent_sources


# ===================== HELPERS =====================

def get_last_opponent_statement(agent_id: str, shared_history: list) -> str:
    my_stance = AGENT_PARAMS[agent_id]["stance"]
    for msg in reversed(shared_history):
        for other_id, other_config in AGENT_PARAMS.items():
            if (other_config["stance"] != my_stance and
                    msg.startswith(other_config["name"] + ":")):
                return msg
    return ""


def get_last_ally_statement(agent_id: str, shared_history: list) -> str:
    my_stance = AGENT_PARAMS[agent_id]["stance"]
    my_name = AGENT_PARAMS[agent_id]["name"]
    for msg in reversed(shared_history):
        for other_id, other_config in AGENT_PARAMS.items():
            if (other_config["stance"] == my_stance and
                    other_config["name"] != my_name and
                    msg.startswith(other_config["name"] + ":")):
                return msg
    return ""


def clean_history(shared_history: list) -> list:
    """Strip refusal/meta lines so they don't pollute agent context."""
    skip_phrases = ["i cannot", "i'm unable", "as an ai", "i won't", "i must clarify"]
    return [
        msg for msg in shared_history
        if not any(phrase in msg.lower() for phrase in skip_phrases)
    ]


# ===================== AGENT RESPONSE =====================

def agent_respond(agent_id: str, shared_history: list, round_num: int) -> str:
    agent_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    p = AGENT_PARAMS[agent_id]

    last_message = shared_history[-1] if len(shared_history) > 1 else ""
    past         = recall_agent_history(agent_id, last_message, n=2)
    sources      = retrieve_agent_sources(agent_id, last_message, n=2)
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

    return reply


# ===================== MODERATOR =====================

def moderator_summary(shared_history: list, round_num: int) -> str:
    mod_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    last_round = shared_history[-(len(AGENT_PARAMS)):]

    response = mod_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        system="""You are a neutral academic moderator evaluating a debate.
Assess only the arguments made. Be brief and analytical.""",
        messages=[{"role": "user", "content": f"""Evaluate Round {round_num}:

{chr(10).join(last_round)}

In 3-4 sentences identify:
- Strongest argument made
- Weakest argument made
- Any logical fallacies
- Whether any position drift occurred"""}]
    )

    summary = response.content[0].text
    print(f"\n📋 MODERATOR (Round {round_num}): {summary}")
    return summary


# ===================== STOPPING CONDITIONS =====================

def score_extremity(agent_id: str, statement: str) -> int:
    response = llm.invoke(
        f"Rate the extremity/hostility of this statement from 1 (very moderate) "
        f"to 10 (very extreme). Return only a number.\nStatement: {statement}"
    )
    try:
        return int(response.content.strip())
    except:
        return 5


def print_extremity_chart(extremity_log: dict):
    """Print a simple ASCII chart of extremity drift across rounds."""
    print("\n📈 EXTREMITY DRIFT")
    print(f"{'Agent':<12}", end="")
    
    max_rounds = max(len(v) for v in extremity_log.values())
    for r in range(1, max_rounds + 1):
        print(f"R{r:<3}", end="")
    print()
    
    for agent_id, scores in extremity_log.items():
        name = AGENT_PARAMS[agent_id]["name"]
        print(f"{name:<12}", end="")
        for s in scores:
            print(f"{s:<4}", end="")
        print()


def should_stop(shared_history: list, round_num: int, max_rounds: int) -> tuple[bool, str]:
    if round_num >= max_rounds:
        return True, f"Maximum rounds ({max_rounds}) reached"

    # Repetition detection after round 4
    if round_num >= 4:
        n = len(AGENT_PARAMS)
        recent  = shared_history[-(n * 2):]
        earlier = shared_history[-(n * 4):-(n * 2)]

        if recent and earlier:
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
    transcript   = "\n".join(shared_history)
    scores_text  = "\n".join([
        f"{AGENT_PARAMS[aid]['name']}: {scores}"
        for aid, scores in extremity_log.items()
    ])

    print(f"\n{'='*60}\nGENERATING ANALYSIS REPORT...\n{'='*60}\n")

    report = llm.invoke(f"""Analyze this debate transcript and write a structured report.

Topic: {topic}
Stop reason: {stop_reason}
Extremity scores per agent per round (1=moderate, 10=extreme):
{scores_text}

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

    # Save outputs
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir   = os.path.join(project_root, "Resources", "simulations")
    os.makedirs(output_dir, exist_ok=True)
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")

    transcript_path = os.path.join(output_dir, f"transcript_{timestamp}.json")
    with open(transcript_path, "w") as f:
        json.dump({
            "topic":         topic,
            "stop_reason":   stop_reason,
            "extremity_log": extremity_log,
            "transcript":    shared_history
        }, f, indent=2)

    print_extremity_chart(extremity_log)            # Visualization
    report_path = os.path.join(output_dir, f"report_{timestamp}.md")
    with open(report_path, "w") as f:
        f.write(f"# Debate Simulation Report\n")
        f.write(f"**Topic:** {topic}\n")
        f.write(f"**Stop reason:** {stop_reason}\n\n")
        f.write(report.content)

    print(report.content)
    print(f"\n📄 Transcript: {transcript_path}")
    print(f"📊 Report:     {report_path}")


# ===================== MAIN SIMULATION LOOP =====================

def run_simulation(topic: str, max_rounds: int = 10):
    shared_history = [f"TOPIC: {topic}"]
    extremity_log  = {agent_id: [] for agent_id in AGENT_PARAMS}
    stop_reason    = f"Maximum rounds ({max_rounds}) reached"

    pro_agents = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "pro"]
    con_agents = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "con"]

    print(f"\n{'='*60}\nDEBATE: {topic}\nAgents: {', '.join([AGENT_PARAMS[a]['name'] for a in AGENT_PARAMS])}\n{'='*60}")

    # Web RAG — each agent searches once
    print("\n🔍 Agents searching for sources...")
    for agent_id in AGENT_PARAMS:
        ingest_agent_sources(agent_id, topic)
    print("✓ Sources ingested\n")

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


# ===================== ENTRY POINT =====================

topic      = input("Enter debate topic: ").strip() or "AI regulation"
max_rounds = input("Max rounds (default 3 for testing): ").strip()
max_rounds = int(max_rounds) if max_rounds.isdigit() else 3
run_simulation(topic, max_rounds)