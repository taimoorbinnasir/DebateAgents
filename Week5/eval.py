import sys, os, json
from anthropic import Anthropic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.agents import AGENT_PARAMS
from shared.tools import llm


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


# ===================== CONCLUSION =====================
def conclude_simulation(topic: str, shared_history: list,
                        extremity_log: dict, stop_reason: str, session_id: str):
    transcript   = "\n".join(shared_history)
    scores_text  = "\n".join([
        f"{AGENT_PARAMS[aid]['name']}: {scores}"
        for aid, scores in extremity_log.items()
    ])

    print(f"\n{'='*60}\nGENERATING ANALYSIS REPORT...\n{'='*60}\n")

    # "llm" imported from shared.tools not used because need
    # larger max_tokens limit to create a final report
    report_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    report_response = report_client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1200,   # hard ceiling as a safety net, not the primary control
    messages=[{"role": "user", "content": f"""Analyze this debate transcript and write a structured report.

Topic: {topic}
Stop reason: {stop_reason}
Extremity scores per agent per round (1=moderate, 10=extreme):
{scores_text}

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

    # Save outputs
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir   = os.path.join(project_root, "Resources", "simulations")
    os.makedirs(output_dir, exist_ok=True)

    transcript_path = os.path.join(output_dir, f"transcript_{session_id}.json")
    report_path     = os.path.join(output_dir, f"report_{session_id}.md")
    with open(transcript_path, "w") as f:
        json.dump({
            "topic":         topic,
            "stop_reason":   stop_reason,
            "extremity_log": extremity_log,
            "transcript":    shared_history
        }, f, indent=2)

    print_extremity_chart(extremity_log)            # Visualization
    with open(report_path, "w") as f:
        f.write(f"# Debate Simulation Report\n")
        f.write(f"**Topic:** {topic}\n")
        f.write(f"**Stop reason:** {stop_reason}\n\n")
        f.write(report_content)

    print(report_content)
    print(f"\n📄 Transcript: {transcript_path}")
    print(f"📊 Report:     {report_path}")