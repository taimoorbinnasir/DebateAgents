# Server-Sent Events Stream Handler
import asyncio, json
from sse_starlette.sse import EventSourceResponse
from fastapi import Request
from .manager import get_simulation

async def simulation_stream(request: Request, session_id: str, manager):
    """Generator that yields SSE events from the simulation queue."""
    
    async def event_generator():
        sim = manager.get_simulation(session_id)
        if not sim:
            yield {"data": json.dumps({"type": "error", "error": "Simulation not found"})}
            return
        
        event_queue = sim["event_queue"]
        
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            try:
                # Non-blocking queue check — run in thread to avoid blocking async loop
                event = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: event_queue.get(timeout=1)
                )
                
                yield {"data": json.dumps(event)}
                
                # Stop streaming when simulation ends
                if event["type"] == "simulation_complete":
                    break
                    
            except Exception:
                # Queue empty — keep waiting
                await asyncio.sleep(0.1)
                continue
    
    return EventSourceResponse(event_generator())


# async def event_generator():
#     sim = get_simulation(session_id)
#     if not sim:
#         yield {"data": json.dumps({"type": "error", "error": "Simulation not found"})}
#         return
    
#     # Replay any events that already happened before connection
#     for past_event in sim["events"]:
#         yield {"data": json.dumps(past_event)}
#         if past_event["type"] == "simulation_complete":
#             return  # already done, no need to listen to queue
    
#     # Now listen for new events
#     event_queue = sim["event_queue"]
#     while True:
#         if await request.is_disconnected():
#             break
#         try:
#             event = await asyncio.get_event_loop().run_in_executor(
#                 None,
#                 lambda: event_queue.get(timeout=1)
#             )
#             yield {"data": json.dumps(event)}
#             if event["type"] == "simulation_complete":
#                 break
#         except Exception:
#             await asyncio.sleep(0.1)
#             continue