import sys, os, threading, queue, json
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from Week5.DebateAgents import run_simulation_streamed

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
    for fname in sorted(os.listdir(sim_dir)):
        if not fname.startswith("transcript_") or not fname.endswith(".json"):
            continue
        fpath = os.path.join(sim_dir, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            # Extract timestamp from filename: transcript_20260810_143022.json
            timestamp = fname.replace("transcript_", "").replace(".json", "")
            results.append({
                "session_id": timestamp,
                "topic":      data.get("topic", "unknown"),
                "timestamp":  timestamp,
                "rounds":     len(data.get("extremity_log", {}).get(
                                  list(data.get("extremity_log", {}).keys())[0], []
                              )) if data.get("extremity_log") else 0,
                "stop_reason": data.get("stop_reason")
            })
        except Exception:
            continue
    
    return list(reversed(results))  # newest first


def start_simulation(session_id: str, topic: str, max_rounds: int):
    """Initialize state and launch simulation in background thread."""
    
    # Per-session event queue — SSE reads from this
    event_queue: queue.Queue = queue.Queue()
    
    _simulations[session_id] = {
        "session_id":    session_id,
        "topic":         topic,
        "status":        "running",
        "current_round": 0,
        "max_rounds":    max_rounds,
        "stop_reason":   None,
        "extremity_log": {},
        "transcript":    [],
        "event_queue":   event_queue,
        "events":      []
    }
    
    # Run simulation in background thread
    thread = threading.Thread(
        target=_run_simulation_thread,
        args=(session_id, topic, max_rounds, event_queue),
        daemon=True
    )
    thread.start()


def _run_simulation_thread(session_id: str, topic: str, 
                            max_rounds: int, event_queue: queue.Queue):
    """Runs inside a background thread. Pushes events to queue."""
    try:
        # Import here to avoid circular imports at module load time
        run_simulation_streamed(
            topic=topic,
            max_rounds=max_rounds,
            session_id=session_id,
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
        
        elif event["type"] == "round_start":
            sim["current_round"] = event["round"]
        
        elif event["type"] == "moderator_summary":
            sim["transcript"].append(f"MODERATOR: {event['text']}")
        
        elif event["type"] == "simulation_complete":
            sim["status"]      = "complete"
            sim["stop_reason"] = event.get("stop_reason", "")