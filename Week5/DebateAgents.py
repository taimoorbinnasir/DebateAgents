import sys, os, random, uuid, json, re
import numpy as np
import queue as q
from anthropic import Anthropic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.agents import AGENT_PARAMS, TEAM_COMPOSITION, build_system_prompt, moderator_summary
from shared.ingest import ingest_agent_sources
from shared.retrieve import retrieve_agent_sources
from shared.tools import llm
from shared.memory import (
    store_agent_statement, recall_agent_history, verify_source_usage,
    store_team_draft, embedder
)
from .helpers import (
    get_last_ally_statement, 
    get_last_opponent_statement, 
    clean_history, 
    should_stop, 
    extract_agent_id_from_message
)
from .eval import (
    score_extremity,
    conclude_simulation,
    score_positions_batch,
    compute_influence_edges
)




# Draft argument for team mode
def agent_draft_argument(agent_id: str, team_name: str, shared_history: list, 
                         round_num: int, session_id: str) -> str:
    """
    Generate ONE candidate argument for this agent's team, for this round.
    This does NOT get spoken publicly — it's a draft, stored in the team's 
    private channel for presenter-selection to evaluate (Part 3).
    """
    agent_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    p = AGENT_PARAMS[agent_id]
    topic = shared_history[0].replace("TOPIC: ", "").strip()
    
    last_message = shared_history[-1] if len(shared_history) > 1 else topic
    past = recall_agent_history(agent_id, last_message, session_id, n=2)
    sources = retrieve_agent_sources(agent_id, last_message, topic, n=2)
    last_opponent = get_last_opponent_statement(agent_id, shared_history)
    debate_lines = clean_history(shared_history)
    
    sections = [f"Current debate on: {shared_history[0]}\n"]
    
    if past:
        sections.append("Your past statements (stay consistent):\n" + "\n".join(past))
    
    if sources:
        cited = "\n".join([f"[{r['source_title']}]: {r['text'][:200]}" for r in sources])
        sections.append(f"Relevant sources (cite naturally if applicable):\n{cited}")
    
    sections.append(
        f"Opponent's most recent argument to address:\n"
        f"{last_opponent if last_opponent else 'No opponent statement yet — open the debate.'}"
    )
    sections.append("Recent conversation:\n" + "\n".join(debate_lines[-8:]))
    
    # Key difference from agent_respond: framed as drafting a PROPOSAL for the team,
    # not as speaking directly — sets up Part 3's selection step correctly
    sections.append(
        f"You are drafting a PROPOSED argument for your team's turn this round. "
        f"Your team will pick the strongest proposal to actually present — "
        f"this may or may not be yours. Write your strongest possible case "
        f"as {p['name']} in 3-5 sentences."
    )
    
    user_content = "\n\n".join(sections)
    
    response = agent_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=build_system_prompt(agent_id),
        messages=[{"role": "user", "content": user_content}]
    )
    
    draft = response.content[0].text
    print(f"  [draft] {p['name']}: {draft[:80]}...")
    
    return draft


def team_brainstorm(team_name: str, shared_history: list, round_num: int, session_id: str) -> list[dict]:
    """
    Each of the 3 agents on this team independently drafts a candidate 
    argument. All 3 drafts are stored in the team's private channel.
    Returns the drafts so Part 3's presenter-selection can use them immediately
    without a redundant DB read.
    """
    agent_ids = TEAM_COMPOSITION[team_name]
    drafts = []
    
    print(f"\n💭 {team_name.upper()} team brainstorming (round {round_num})...")
    
    for agent_id in agent_ids:
        draft = agent_draft_argument(agent_id, team_name, shared_history, round_num, session_id)
        store_team_draft(team_name, agent_id, draft, round_num, session_id)
        drafts.append({"agent_id": agent_id, "draft": draft})
    
    return drafts



# ===================== AGENT RESPONSE =====================
def agent_respond(agent_id: str, shared_history: list, round_num: int, session_id: str) -> str:
    topic = shared_history[0].replace("TOPIC: ", "").strip()
    agent_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    p = AGENT_PARAMS[agent_id]

    last_message = shared_history[-1] if len(shared_history) > 1 else topic
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

    verified_sources = verify_source_usage(reply, sources)
    # print(f"DEBUG {agent_id}: {len(sources)} retrieved, {len(verified_sources)} verified")

    # Return sources alongside the reply — this is the key change
    cited_sources = [
        {"title": s["source_title"], "url": s["source_url"], "similarity": s["similarity"]}
        for s in verified_sources    # ← fixed: iterate over verified_sources
    ]
    return reply, cited_sources


# ===================== MAIN SIMULATION LOOP =====================
def run_simulation(topic: str, max_rounds: int = 10):
    session_id = str(uuid.uuid4())[:8]
    shared_history = [f"TOPIC: {topic}"]
    extremity_log  = {agent_id: [] for agent_id in AGENT_PARAMS}
    stop_reason    = f"Maximum rounds ({max_rounds}) reached"

    pro_agents = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "pro"]
    con_agents = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "con"]

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

    conclude_simulation(topic, shared_history, extremity_log, stop_reason, session_id)


# ===================== SIMULATION LOOP FOR BACKEND =====================
# Simulation loop that pushes events to a queue instead of printing
def run_individual_round_loop(topic: str, max_rounds: int, session_id: str, 
                             mode: str = "individual", event_queue=None):
    """
    mode: "individual" (current 6-agent behavior, default, unchanged) 
          or "team" (3v3 brainstorm+presenter behavior, Part 2-4 of Week 8)
    """
    # If no queue provided, fall back to print behavior
    def push(event: dict):
        from backend.manager import push_event
        push_event(session_id, event) if event_queue else print(event)

    # Push research phase start
    push({"type": "research_start", "total_agents": len(AGENT_PARAMS)})
    
    shared_history = [f"TOPIC: {topic}"]
    extremity_log  = {agent_id: [] for agent_id in AGENT_PARAMS}
    stop_reason    = f"Maximum rounds ({max_rounds}) reached"

    pro_agents     = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "pro"]
    con_agents     = [a for a in AGENT_PARAMS if AGENT_PARAMS[a]["stance"] == "con"]

    try:
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

        structured_statements = []
        position_log = {agent_id: [] for agent_id in AGENT_PARAMS}
        targeting_log = []  # [{round, speaker, target}]
        for round_num in range(1, max_rounds + 1):
            push({"type": "round_start", "round": round_num, "max_rounds": max_rounds})
            
            random.shuffle(pro_agents)
            random.shuffle(con_agents)
            turn_order = [x for pair in zip(pro_agents, con_agents) for x in pair]

            round_statements = {}  # collect this round's statements for batch scoring

            for agent_id in turn_order:
                # Find who this agent is about to address BEFORE generating the reply
                last_opponent_msg = get_last_opponent_statement(agent_id, shared_history)
                target_id = extract_agent_id_from_message(last_opponent_msg) if last_opponent_msg else None

                reply, cited_sources = agent_respond(agent_id, shared_history, round_num, session_id)
                statement = f"{AGENT_PARAMS[agent_id]['name']}: {reply}"
                shared_history.append(statement)
                store_agent_statement(agent_id, reply, round_num, session_id)

                score = score_extremity(agent_id, reply)
                extremity_log[agent_id].append(score)
                round_statements[agent_id] = reply
                
                if target_id:
                    targeting_log.append({"round": round_num, "speaker": agent_id, "target": target_id})
                
                push({
                    "type":       "agent_statement",
                    "agent_id":   agent_id,
                    "agent_name": AGENT_PARAMS[agent_id]["name"],
                    "stance":     AGENT_PARAMS[agent_id]["stance"],
                    "round_num":  round_num,
                    "text":       reply,
                    "extremity":  score,
                    "sources":    cited_sources
                })

            # Batch score positions for this round — ONE call, not six
            round_positions = score_positions_batch(round_statements, topic)
            for agent_id in AGENT_PARAMS:
                score = round_positions.get(agent_id, 0)
                position_log[agent_id].append(score)

            push({"type": "position_update", "round": round_num, "positions": round_positions})
            structured_statements.append({
                "agent_id":   agent_id,
                "agent_name": AGENT_PARAMS[agent_id]["name"],
                "stance":     AGENT_PARAMS[agent_id]["stance"],
                "round_num":  round_num,
                "text":       reply,
                "sources":    cited_sources
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
    except Exception as e:
        stop_reason = f"Simulation interrupted: {str(e)}"
        push({"type": "error", "error": str(e)})
    finally:
        # ALWAYS save whatever we have, even if interrupted
        influence_edges = compute_influence_edges(position_log, targeting_log)

        # Push each edge as an event so manager.py's push_event picks it up
        for edge in influence_edges:
            push({
                "type": "influence_edge",
                "from": edge["from"],
                "to": edge["to"],
                "round": edge["round"],
                "weight": edge["weight"]
            })

        conclude_simulation(topic, shared_history, extremity_log, stop_reason, 
                            session_id, position_log, influence_edges, structured_statements)
        push({"type": "simulation_complete", "stop_reason": stop_reason})




def select_presenter(team_name: str, drafts: list[dict], shared_history: list) -> dict:
    """
    Evaluate 3 draft arguments from one team and select the strongest.
    Returns the winning draft along with which agent presented it.
    """
    presenter_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    topic = shared_history[0].replace("TOPIC: ", "").strip()
    last_opponent_stmt = shared_history[-1] if len(shared_history) > 1 else "No opponent statement yet."
    
    drafts_text = "\n\n".join([
        f"[Option {i+1} — {AGENT_PARAMS[d['agent_id']]['name']}]: {d['draft']}"
        for i, d in enumerate(drafts)
    ])
    
    response = presenter_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        system="""You are selecting the strongest argument for a debate team to present. 
Evaluate based on: relevance to the opponent's last point, persuasiveness, and clarity.
Return ONLY the option number (1, 2, or 3), nothing else.""",
        messages=[{"role": "user", "content": f"""Topic: {topic}

Opponent's last statement to respond to:
{last_opponent_stmt}

Candidate arguments from the {team_name.upper()} team:
{drafts_text}

Which option is strongest? Reply with ONLY the number."""}]
    )
    
    raw = response.content[0].text.strip()
    
    try:
        selected_idx = int(raw[0]) - 1  # take first digit, handle "1" or "1." etc.
        if selected_idx < 0 or selected_idx >= len(drafts):
            selected_idx = 0  # fallback if the model returns something unexpected
    except (ValueError, IndexError):
        selected_idx = 0  # safe fallback — presenter selection failed, default to first draft
    
    selected = drafts[selected_idx]
    print(f"  🎤 Presenter for {team_name.upper()}: {AGENT_PARAMS[selected['agent_id']]['name']} (option {selected_idx + 1})")
    
    return selected


presenter_log = {"pro": [], "con": []}  # which agent_id presented each round, per team



def score_team_positions_batch(round_statements: dict, topic: str) -> dict:
    """Same batching pattern as score_positions_batch, but keyed by team name."""
    lines = "\n".join([f"{team}: {stmt}" for team, stmt in round_statements.items()])
    
    prompt = f"""For each statement below, score where the speaker's TEAM stands on 
'{topic}' from -10 (fully opposed) to +10 (fully in favor).

Return ONLY a JSON object mapping team name to score, nothing else, no markdown fences.
Example format: {{"pro": 8, "con": -7}}

Statements:
{lines}"""

    response = llm.invoke(prompt)
    try:
        raw = response.content.strip()
        raw = re.sub(r"```(?:json)?\n?", "", raw).strip()
        return json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        print(f"  ⚠️ Could not parse team position scores")
        return {team: 0 for team in round_statements}



def should_stop_team(shared_history: list, round_num: int, max_rounds: int) -> tuple[bool, str]:
    if round_num >= max_rounds:
        return True, f"Maximum rounds ({max_rounds}) reached"
    
    if round_num >= 4:
        n = 2  # team mode: 2 statements per round, not 6
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




def run_team_round_loop(topic: str, max_rounds: int, session_id: str, event_queue=None):
    def push(event):
        if event_queue:
            from backend.manager import push_event
            push_event(session_id, event)
        else:
            print(event)
    
    team_position_log  = {"pro": [], "con": []}
    team_extremity_log = {"pro": [], "con": []}
    presenter_log       = {"pro": [], "con": []}
    shared_history = [f"TOPIC: {topic}"]
    stop_reason = f"Maximum rounds ({max_rounds}) reached"
    
    all_agent_ids = TEAM_COMPOSITION["pro"] + TEAM_COMPOSITION["con"]
    push({"type": "research_start", "total_agents": len(all_agent_ids)})
    for i, agent_id in enumerate(all_agent_ids):
        ingest_agent_sources(agent_id, topic, session_id)
        push({"type": "research_progress", "completed": i + 1, "total": len(all_agent_ids)})
    push({"type": "research_complete"})
    
    try:
        for round_num in range(1, max_rounds + 1):
            push({"type": "round_start", "round": round_num, "max_rounds": max_rounds})
            
            round_statements = {}  # collect for batch position scoring
            
            for team_name in ["pro", "con"]:
                drafts = team_brainstorm(team_name, shared_history, round_num, session_id)
                selected = select_presenter(team_name, drafts, shared_history)
                presenter_agent_id = selected["agent_id"]
                statement_text = selected["draft"]
                
                presenter_name = AGENT_PARAMS[presenter_agent_id]["name"]
                statement = f"{team_name.upper()} TEAM ({presenter_name}): {statement_text}"
                shared_history.append(statement)
                presenter_log[team_name].append(presenter_agent_id)
                
                store_agent_statement(presenter_agent_id, statement_text, round_num, session_id)
                
                score = score_extremity(presenter_agent_id, statement_text)
                team_extremity_log[team_name].append(score)
                round_statements[team_name] = statement_text
                
                push({
                    "type": "agent_statement",
                    "agent_id": team_name,
                    "agent_name": f"{team_name.upper()} Team ({presenter_name})",
                    "stance": team_name,
                    "round_num": round_num,
                    "text": statement_text,
                    "extremity": score,
                    "presenter": presenter_agent_id
                })
            
            # Batch position scoring — ONE call for both teams this round
            round_positions = score_team_positions_batch(round_statements, topic)
            for team_name in ["pro", "con"]:
                pos = round_positions.get(team_name, 0)
                team_position_log[team_name].append(pos)
            push({"type": "position_update", "round": round_num, "positions": round_positions})
            
            # Moderator — reuse existing function unchanged, works on shared_history regardless of mode
            mod_text = moderator_summary(shared_history, round_num)
            shared_history.append(f"MODERATOR: {mod_text}")
            push({"type": "moderator_summary", "round": round_num, "text": mod_text})
            
            # Stopping conditions — reuse existing should_stop, 
            # but note: it checks len(AGENT_PARAMS) for repetition detection, 
            # which assumes 6 agents — needs a team-aware variant
            stop, reason = should_stop_team(shared_history, round_num, max_rounds)
            if stop:
                stop_reason = reason
                break
    
    except Exception as e:
        stop_reason = f"Simulation interrupted: {str(e)}"
        push({"type": "error", "error": str(e)})
    
    finally:
        conclude_simulation(topic, shared_history, team_extremity_log, stop_reason, 
                           session_id, team_position_log, [])  # empty influence_edges — team mode doesn't use per-agent influence tracking (see note below)
        push({"type": "simulation_complete", "stop_reason": stop_reason})



def run_simulation_streamed(topic: str, max_rounds: int, session_id: str, 
                             mode: str = "individual", event_queue=None):
    """
    Entry point — dispatches to the correct simulation mode.
    
    mode: "individual" (default, current 6-agent behavior, unchanged) 
          or "team" (3v3 brainstorm+presenter mode, built out in Parts 2-4)
    """
    if mode == "team":
        return run_team_round_loop(topic, max_rounds, session_id, event_queue)
    else:
        return run_individual_round_loop(topic, max_rounds, session_id, event_queue)


# ===================== ENTRY POINT =====================
if __name__ == "__main__":
    topic      = input("Enter debate topic: ").strip() or "AI regulation"
    max_rounds = input("Max rounds (default 3 for testing): ").strip()
    max_rounds = int(max_rounds) if max_rounds.isdigit() else 3
    run_simulation(topic, max_rounds)