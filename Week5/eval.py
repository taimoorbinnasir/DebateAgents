import sys, os, json, re
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.agents import AGENT_PARAMS
from shared.config import LANGUAGE_INSTRUCTION
from shared.run_context import response_text


def display_name(log_key: str) -> str:
    """Log keys are agent_ids in individual mode, but 'pro'/'con' in team mode."""
    if log_key in AGENT_PARAMS:
        return AGENT_PARAMS[log_key]["name"]
    return f"{log_key.upper()} team"


# ===================== EXTREMITY =====================
# Scorers call the SDK directly (previously the LangChain `llm`). max_tokens=1024 is the
# ChatAnthropic default they were sent with, so the requests are unchanged.
SCORER_MAX_TOKENS = 1024


def score_extremity(agent_id: str, statement: str, *, ctx, round_num: int | None = None) -> int:
    response = ctx.create(
        "extremity_scorer", round_num=round_num, agent_id=agent_id,
        max_tokens=SCORER_MAX_TOKENS,
        messages=[{"role": "user", "content":
            f"Rate the extremity/hostility of this statement from 1 (very moderate) "
            f"to 10 (very extreme). Return only a number.\nStatement: {statement}"}]
    )
    try:
        return int(response_text(response).strip())
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
        name = display_name(agent_id)
        print(f"{name:<12}", end="")
        for s in scores:
            print(f"{s:<4}", end="")
        print()


# ===================== BATCH SCORE =====================
def score_positions_batch(round_statements: dict, topic: str, *, ctx, round_num: int | None = None) -> dict:
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

    response = ctx.create(
        "position_scorer", round_num=round_num,
        max_tokens=SCORER_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        # Strip markdown fences if present — same fix you used for fact extraction
        raw = response_text(response).strip()
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
def infer_mode(extremity_log: dict) -> str:
    """For transcripts saved before the `mode` field existed: team runs log only 'pro'/'con'."""
    keys = set(extremity_log or {})
    return "team" if keys and keys <= {"pro", "con"} else "individual"


def _format_log(log: dict) -> str:
    return "\n".join([f"{display_name(k)}: {scores}" for k, scores in (log or {}).items()])


def _individual_report_prompt(topic, stop_reason, scores_text, position_text,
                              influence_edges, transcript) -> str:
    influence_text = ""
    if influence_edges:
        influence_text = "\n".join([
            f"{AGENT_PARAMS[e['from']]['name']} → {AGENT_PARAMS[e['to']]['name']} "
            f"(round {e['round']}, weight {e['weight']})"
            for e in influence_edges
        ])

    return f"""Analyze this debate transcript and write a structured report.

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
{transcript}"""


def _team_report_prompt(topic, stop_reason, scores_text, position_text,
                        presenter_log, transcript) -> str:
    rounds = max((len(v) for v in (presenter_log or {}).values()), default=0)
    presenter_text = "\n".join([
        f"Round {r + 1}: " + ", ".join(
            f"{team.upper()} team → {AGENT_PARAMS[ids[r]]['name']} ({AGENT_PARAMS[ids[r]]['reasoning_style']}, "
            f"extremity trait {AGENT_PARAMS[ids[r]]['extremity']}/10)"
            for team, ids in presenter_log.items() if r < len(ids)
        )
        for r in range(rounds)
    ])

    return f"""Analyze this TEAM debate transcript and write a structured report.

{LANGUAGE_INSTRUCTION}
Format: two teams of three agents each. Every round, each team privately drafted and critiqued
proposals, then ONE member (the presenter) wrote the team's single public statement in their own
persona voice. Presenters rotate in a fixed order with a random starting member — they are NOT
chosen on merit, so do not treat who presented as a judgment of quality.

Topic: {topic}
Stop reason: {stop_reason}
Extremity scores per team per round (1=moderate, 10=extreme):
{scores_text}

Position scores per team per round (-10 to +10, where the team stood on the topic):
{position_text if position_text else "Not tracked for this run."}

Presenter each round (with the presenter's persona):
{presenter_text if presenter_text else "Not recorded."}

STRICT LENGTH LIMIT: Write no more than 350 words total. Each section must be 
2-3 sentences maximum. Be direct — state conclusions, not reasoning chains.
Do not restate the scores or transcript back to the reader.

## 1. Position Drift
In 2-3 sentences: did either team shift position? Which team held firmer?

## 2. Presenter Effect
In 2-3 sentences: did a team's tone or extremity visibly change with who presented? Treat this as
correlation, not proof — each statement also reflects the whole team's brainstorm.

## 3. Radicalization
In 2-3 sentences: did either team become more extreme over the rounds? What triggered it?

## 4. Fault Lines
In 2-3 sentences: what was the core unresolvable disagreement between the teams?

## 5. Verdict
In 1-2 sentences: which team argued most effectively on evidence quality alone?

Transcript:
{transcript}"""


def conclude_simulation(topic: str, shared_history: list,
                        extremity_log: dict, stop_reason: str, session_id: str,
                        position_log: dict = None, influence_edges: list = None,
                        structured_statements: list = None, mode: str = "individual",
                        presenter_log: dict = None, brainstorm_log: list = None,
                        *, ctx, experiment_id: str | None = None, output_dir: str | None = None):
    """output_dir defaults to Resources/simulations/ (what the History page reads);
    experiment runs pass their own folder so they don't flood History."""
    transcript    = "\n".join(shared_history)
    scores_text   = _format_log(extremity_log)
    position_text = _format_log(position_log)

    if mode == "team":
        prompt = _team_report_prompt(topic, stop_reason, scores_text, position_text,
                                     presenter_log, transcript)
    else:
        prompt = _individual_report_prompt(topic, stop_reason, scores_text, position_text,
                                           influence_edges, transcript)

    print(f"\n{'='*60}\nGENERATING ANALYSIS REPORT...\n{'='*60}\n")

    report_response = ctx.create(
        "report",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )
    report_content = response_text(report_response)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir   = output_dir or os.path.join(project_root, "Resources", "simulations")
    os.makedirs(output_dir, exist_ok=True)

    transcript_path = os.path.join(output_dir, f"transcript_{session_id}.json")
    report_path     = os.path.join(output_dir, f"report_{session_id}.md")

    saved = {
        "saved_at":        datetime.now().isoformat(timespec="seconds"),
        "mode":            mode,
        "topic":           topic,
        "stop_reason":     stop_reason,
        "extremity_log":   extremity_log,
        "position_log":    position_log or {},
        "influence_edges": influence_edges or [],
        "transcript":      shared_history,
        "statements":      structured_statements or [],
        # Model comparison: what produced this run, and what it cost (report call included)
        "model_config":    ctx.model_config(),
        "cost_log":        ctx.cost_log,
        "total_cost_usd":  round(ctx.total_cost(), 6),
        "experiment_id":   experiment_id,
        "seed":            ctx.seed,
    }
    if mode == "team":
        saved["presenter_log"]  = presenter_log or {}
        saved["brainstorm_log"] = brainstorm_log or []

    with open(transcript_path, "w") as f:
        json.dump(saved, f, indent=2)

    print_extremity_chart(extremity_log)
    with open(report_path, "w") as f:
        f.write(f"# Debate Simulation Report\n")
        f.write(f"**Mode:** {'Team' if mode == 'team' else 'Individual'}\n")
        f.write(f"**Topic:** {topic}\n")
        f.write(f"**Stop reason:** {stop_reason}\n\n")
        f.write(report_content)

    print(report_content)
    print(f"\n📄 Transcript: {transcript_path}")
    print(f"📊 Report:     {report_path}")
