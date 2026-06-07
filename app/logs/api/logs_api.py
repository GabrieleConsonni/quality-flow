from fastapi import APIRouter

from _alembic.services.session_context_manager import managed_session
from logs.services.alembic.log_service import LogService

router = APIRouter(prefix="/logs")

@router.get("/")
async def get_logs_api() -> list[dict]:
    with managed_session() as session:
        results=[]
        logs = LogService().get_logs(session)
        for log in logs:
            results.append({
                "id": log.id,
                "subject_type": log.subject_type,
                "subject": log.subject,
                "message": log.message,
                "level": log.level,
                "payload": log.payload,
                "created_at": log.created_at
            })
        return results

@router.delete("/{days}")
async def clear_logs_api(days:int) -> dict[str, str]:
    with managed_session() as session:
        LogService().clean_logs(session,days)
    return {"message": "All logs cleared successfully"}