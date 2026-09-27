import sys, os, threading, queue, json
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from Week5.DebateAgents import run_simulation_streamed
from Week5.eval import infer_mode

from backend.models import SimulationStatus, AgentStatement, ModeratorSummary

# Active simulations keyed by session_id
_simulations: dict[str, dict] = {}

def get_simulation(session_id: str) -> dict | None:
    return _simulations.get(session_id)

def get_all_simulations() -> list[dict]:
    """Load metadata from all saved transcript files."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sim_dir = os.path.join(project_root, "Resources", "simulations")
    
    if not os.path.exists(sim_dir):
        return []
    
    results = []
    for fname in os.listdir(sim_dir):
        if not fname.startswith("transcript_") or not fname.endswith(".json"):
            continue
        fpath = os.path.join(sim_dir, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            # Filenames are session ids (transcript_<session_id>.json), not dates — recency comes
            # from saved_at, or the file's modified time for runs saved before saved_at existed
            timestamp = fname.replace("transcript_", "").replace(".json", "")
            saved_at = data.get("saved_at") or datetime.fromtimestamp(
                os.path.getmtime(fpath)).isoformat(timespec="seconds")
            results.append({
                "session_id": timestamp,
                "topic":      data.get("topic", "unknown"),
                "timestamp":  timestamp,
                "rounds":     len(data.get("extremity_log", {}).get(
                                  list(data.get("extremity_log", {}).keys())[0], []
                              )) if data.get("extremity_log") else 0,
                "stop_reason": data.get("stop_reason"),
                "mode":        data.get("mode") or infer_mode(data.get("extremity_log")),
                "saved_at":    saved_at
            })
        except Exception:
            continue
    
    return sorted(results, key=lambda r: r["saved_at"], reverse=True)  # newest first


def start_simulation(session_id: str, topic: str, max_rounds: int, mode: str = "individual"):
    """Initialize state and launch simulation in background thread."""
    
    # Per-session event queue — SSE reads from this
    event_queue: queue.Queue = queue.Queue()
    
    _simulations[session_id] = {
        "session_id":    session_id,
        "topic":         topic,
        "mode":          mode,
        "status":        "running",
        "current_round": 0,
        "max_rounds":    max_rounds,
        "stop_reason":   None,
        "extremity_log": {},
        "position_log":    {},
        "influence_edges": [],
        "user_opinions":   [],
        "transcript":    [],
        "event_queue":   event_queue,
        "events":      []
    }
    
    # Run simulation in background thread
    thread = threading.Thread(
        target=_run_simulation_thread,
        args=(session_id, topic, max_rounds, mode, event_queue),
        daemon=True
    )
    thread.start()


def _run_simulation_thread(session_id: str, topic: str, 
                            max_rounds: int, mode: str, event_queue: queue.Queue):
    """Runs inside a background thread. Pushes events to queue."""
    try:
        # Import here to avoid circular imports at module load time
        run_simulation_streamed(
            topic=topic,
            max_rounds=max_rounds,
            session_id=session_id,
            mode=mode,
            event_queue=event_queue
        )
    except Exception as e:
        _simulations[session_id]["status"] = "error"
        _simulations[session_id]["stop_reason"] = str(e)
        event_queue.put({
            "type":  "error",
            "error": str(e)
        })
    finally:
        # Signal SSE stream to close
        event_queue.put({"type": "simulation_complete"})


def push_event(session_id: str, event: dict):
    """Called by simulation to push an event to the SSE queue."""
    sim = _simulations.get(session_id)
    if sim:
        # Sequence number: after a reconnect, the snapshot and the reopened stream can both
        # contain events pushed while the client was away — the frontend drops seq it has seen
        event["seq"] = len(sim["events"])
        sim["event_queue"].put(event)
        sim["events"].append(event)  # persist all events
        
        # Also update local state for status endpoint
        if event["type"] == "agent_statement":
            agent_id = event["agent_id"]
            score    = event["extremity"]
            if agent_id not in sim["extremity_log"]:
                sim["extremity_log"][agent_id] = []
            sim["extremity_log"][agent_id].append(score)
            sim["transcript"].append(f"{event['agent_name']}: {event['text']}")

        elif event["type"] == "position_update":
            for agent_id, score in event["positions"].items():
                if agent_id not in sim["position_log"]:
                    sim["position_log"][agent_id] = []
                sim["position_log"][agent_id].append(score)

        elif event["type"] == "influence_edge":
            sim["influence_edges"].append({
                "from":   event["from"],
                "to":     event["to"],
                "round":  event["round"],
                "weight": event["weight"]
            })
        
        elif event["type"] == "round_start":
            sim["current_round"] = event["round"]
        
        elif event["type"] == "moderator_summary":
            sim["transcript"].append(f"MODERATOR: {event['text']}")
        
        elif event["type"] == "simulation_complete":
            sim["status"]      = "complete"
            sim["stop_reason"] = event.get("stop_reason", "")


def record_opinion(session_id: str, opinion: dict):
    sim = _simulations.get(session_id)
    if sim:
        sim["user_opinions"].append(opinion)