import sys, os, json, re
from anthropic import Anthropic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.agents import AGENT_PARAMS
from shared.config import LANGUAGE_INSTRUCTION
from shared.tools import llm


# ===================== EXTREMITY =====================
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


# ===================== BATCH SCORE =====================
def score_positions_batch(round_statements: dict, topic: str) -> dict:
    """One LLM call scores all agents' positions for a round.
    round_statements: {agent_id: statement_text}
    Returns: {agent_id: position_score}
    """
    lines = "\n".join([f"{aid}: {stmt}" for aid, stmt in round_statements.items()])
    
    prompt = f"""For each statement below, score where the speaker stands on '{topic}' 
from -10 (fully opposed) to +10 (fully in favor). Base the score only on what they 
actually said this round, not their known reputation.

Return ONLY a JSON object mapping agent_id to score, nothing else, no markdown fences.
Example format: {{"pro_hardliner": 8, "con_hardliner": -9}}

Statements:
{lines}"""

    response = llm.invoke(prompt)
    
    try:
        # Strip markdown fences if present — same fix you used for fact extraction
        raw = response.content.strip()
        raw = re.sub(r"```(?:json)?\n?", "", raw).strip()
        return json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        print(f"  ⚠️ Could not parse position scores, defaulting to 0")
        return {aid: 0 for aid in round_statements}


def compute_influence_edges(position_log: dict, targeting_log: list) -> list:
    """For each addressing event, check if the speaker's position moved
    toward the target's position in the following round. Zero LLM cost —
    this is correlation-based, not proof of causation."""
    edges = []
    
    for t in targeting_log:
        speaker, target, round_num = t["speaker"], t["target"], t["round"]
        
        # Need positions before AND after this round for the speaker
        if round_num < 1 or round_num >= len(position_log[speaker]):
            continue
        if round_num - 1 >= len(position_log[target]):
            continue
        
        pos_before = position_log[speaker][round_num - 1] if round_num >= 1 else position_log[speaker][0]
        pos_after  = position_log[speaker][round_num]
        target_pos = position_log[target][round_num - 1]
        
        dist_before = abs(pos_before - target_pos)
        dist_after  = abs(pos_after - target_pos)
        
        if dist_after < dist_before:
            edges.append({
                "from": target,
                "to": speaker,
                "round": round_num,
                "weight": round(dist_before - dist_after, 1)
            })
    
    return edges


# ===================== CONCLUSION =====================
def conclude_simulation(topic: str, shared_history: list,
                        extremity_log: dict, stop_reason: str, session_id: str,
                        position_log: dict = None, influence_edges: list = None,
                        structured_statements: list = None):
    transcript   = "\n".join(shared_history)
    scores_text  = "\n".join([
        f"{AGENT_PARAMS[aid]['name']}: {scores}"
        for aid, scores in extremity_log.items()
    ])

    # Format position data for the report prompt (optional but useful context)
    position_text = ""
    if position_log:
        position_text = "\n".join([
            f"{AGENT_PARAMS[aid]['name']}: {scores}"
            for aid, scores in position_log.items()
        ])

    influence_text = ""
    if influence_edges:
        influence_text = "\n".join([
            f"{AGENT_PARAMS[e['from']]['name']} → {AGENT_PARAMS[e['to']]['name']} "
            f"(round {e['round']}, weight {e['weight']})"
            for e in influence_edges
        ])

    print(f"\n{'='*60}\nGENERATING ANALYSIS REPORT...\n{'='*60}\n")

    report_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    report_response = report_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1200,
        messages=[{"role": "user", "content": f"""Analyze this debate transcript and write a structured report.

{LANGUAGE_INSTRUCTION}
Topic: {topic}
Stop reason: {stop_reason}
Extremity scores per agent per round (1=moderate, 10=extreme):
{scores_text}

Position scores per agent per round (-10 to +10, where the agent stood on the topic):
{position_text if position_text else "Not tracked for this run."}

Detected influence patterns (engagement-correlated position drift, not proven causation):
{influence_text if influence_text else "None detected."}

STRICT LENGTH LIMIT: Write no more than 350 words total. Each section must be 
2-3 sentences maximum. Be direct — state conclusions, not reasoning chains.
Do not restate the extremity scores or transcript back to the reader.

## 1. Position Drift
In 2-3 sentences: did any agent shift position? Who moved most, who was immovable?

## 2. Influence Map
In 2-3 sentences: which agent had the most impact on the conversation's direction?

## 3. Radicalization
In 2-3 sentences: did any agent become more extreme? What triggered it?

## 4. Fault Lines
In 2-3 sentences: what was the core unresolvable disagreement?

## 5. Verdict
In 1-2 sentences: who argued most effectively on evidence quality alone?

Transcript:
{transcript}"""}]
    )
    report_content = report_response.content[0].text

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir   = os.path.join(project_root, "Resources", "simulations")
    os.makedirs(output_dir, exist_ok=True)

    transcript_path = os.path.join(output_dir, f"transcript_{session_id}.json")
    report_path     = os.path.join(output_dir, f"report_{session_id}.md")

    with open(transcript_path, "w") as f:
        json.dump({
            "topic":           topic,
            "stop_reason":     stop_reason,
            "extremity_log":   extremity_log,
            "position_log":    position_log or {},
            "influence_edges": influence_edges or [],
            "transcript":      shared_history,
            "statements": structured_statements or []
        }, f, indent=2)

    print_extremity_chart(extremity_log)
    with open(report_path, "w") as f:
        f.write(f"# Debate Simulation Report\n")
        f.write(f"**Topic:** {topic}\n")
        f.write(f"**Stop reason:** {stop_reason}\n\n")
        f.write(report_content)

    print(report_content)
    print(f"\n📄 Transcript: {transcript_path}")
    print(f"📊 Report:     {report_path}")