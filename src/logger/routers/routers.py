from fastapi import APIRouter, Query, status
from typing import List, Optional, Dict, Any
from ..mongo.models import LogEntry
from ..mongo.database import logs_collection

Router = APIRouter(prefix="/logger", tags=["Logs"])

@Router.get(
    "/",
    response_model=List[LogEntry],
    summary="Retrieve aggregated logs",
    description="Get logs from MongoDB with optional filtering. Returns latest logs first."
)
async def get_logs(
    limit: int = Query(100, ge=1, le=10000, description="Max number of logs to return"),
    log_type: Optional[str] = Query(None, description="Filter by log type (CMD, EVENT, LOG)"),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, ERROR, WARN)")
):
    mongo_query: Dict[str, Any] = {}

    if log_type:
        mongo_query["log_type"] = log_type
    if level:
        mongo_query["level"] = level

    cursor = logs_collection.find(mongo_query).sort("timestamp", -1).limit(limit)

    results = []
    async for document in cursor:
        document.pop("_id", None)
        results.append(document)

    return results


@Router.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    status_code=status.HTTP_200_OK
)
async def health_check():
    return {"status": "ok", "service": "log-aggregation"}
