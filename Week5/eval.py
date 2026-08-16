import sys, os, json
from datetime import datetime
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