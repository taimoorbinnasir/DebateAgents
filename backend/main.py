import sys, os, uuid, json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import Request, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models import (
    SimulationRequest, SimulationStatus,
    SimulationTranscript, SimulationMeta
)
import backend.manager as manager
from .models import UserOpinion
from .sse import simulation_stream

app = FastAPI(title="Debate Simulation API")

# CORS — allow Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/simulation/start")
def start_simulation(req: SimulationRequest):
    session_id = str(uuid.uuid4())[:8]
    manager.start_simulation(session_id, req.topic, req.max_rounds)
    return {"session_id": session_id, "status": "started"}


@app.get("/simulation/{session_id}/status", response_model=SimulationStatus)
def get_status(session_id: str):
    sim = manager.get_simulation(session_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationStatus(
        session_id=    sim["session_id"],
        topic=         sim["topic"],
        status=        sim["status"],
        current_round= sim["current_round"],
        max_rounds=    sim["max_rounds"],
        stop_reason=   sim["stop_reason"],
        extremity_log= sim["extremity_log"],
        position_log=    sim["position_log"],
        influence_edges= sim["influence_edges"],
        user_opinions=   sim["user_opinions"]
    )


@app.get("/simulation/{session_id}/transcript", response_model=SimulationTranscript)
def get_transcript(session_id: str):
    sim = manager.get_simulation(session_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationTranscript(
        session_id=    sim["session_id"],
        topic=         sim["topic"],
        stop_reason=   sim["stop_reason"] or "",
        transcript=    sim["transcript"],
        extremity_log= sim["extremity_log"]
    )


@app.get("/simulations", response_model=list[SimulationMeta])
def list_simulations():
    return manager.get_all_simulations()


@app.get("/simulation/{session_id}/stream")
async def stream_simulation(session_id: str, request: Request):
    return await simulation_stream(request, session_id, manager)


@app.get("/simulation/{session_id}/events")
def get_events(session_id: str):
    """Return all events for an active in-memory simulation."""
    sim = manager.get_simulation(session_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"events": sim["events"]}


@app.get("/simulations/{timestamp}/detail", response_model=SimulationTranscript)
def get_saved_simulation(timestamp: str):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(project_root, "Resources", "simulations", f"transcript_{timestamp}.json")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Simulation transcript not found")
    
    with open(filepath) as f:
        data = json.load(f)
    
    return SimulationTranscript(
        session_id=    timestamp,
        topic=         data.get("topic", ""),
        stop_reason=   data.get("stop_reason", ""),
        transcript=    data.get("transcript", []),
        extremity_log= data.get("extremity_log", {}),
        position_log=    data.get("position_log", {}),
        influence_edges= data.get("influence_edges", []),
        user_opinions=   data.get("user_opinions", [])
    )


@app.get("/simulations/{timestamp}/report")
def get_report(timestamp: str):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(project_root, "Resources", "simulations", f"report_{timestamp}.md")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")
    
    with open(filepath) as f:
        content = f.read()
    
    return {"content": content}


@app.get("/simulation/{session_id}/snapshot")
def get_snapshot(session_id: str):
    sim = manager.get_simulation(session_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {
        "status": sim["status"],
        "events": sim["events"],  # everything that's happened so far
        "extremity_log": sim["extremity_log"],
        "position_log":    sim["position_log"],
        "influence_edges": sim["influence_edges"],
        "user_opinions":   sim["user_opinions"],
        "topic": sim["topic"],
        "max_rounds": sim["max_rounds"]
    }


@app.post("/simulation/{session_id}/opinion")
def submit_opinion(session_id: str, opinion: UserOpinion):
    sim = manager.get_simulation(session_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    manager.record_opinion(session_id, opinion.dict())
    return {"status": "recorded"}