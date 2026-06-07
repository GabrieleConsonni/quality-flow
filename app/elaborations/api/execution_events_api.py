from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from elaborations.services.suite_runs.execution_event_bus import stream_execution_events

router = APIRouter(prefix="/elaborations")


@router.get("/execution/{execution_id}/events")
async def stream_execution_events_api(execution_id: str):
    return StreamingResponse(
        stream_execution_events(execution_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

