from fastapi import APIRouter, Query, status
from typing import List, Optional, Dict, Any
from ..mongo.models import LogEntry, Message
from ..mongo.database import logs_collection
from chassis.messaging import is_rabbitmq_healthy
from chassis.routers import (
    get_system_metrics,
    raise_and_log_error,
)
from ..messaging.global_vars import (
    RABBITMQ_CONFIG,
    PUBLIC_KEY
)
from chassis.security import create_jwt_verifier

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException,
    status
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import (
    List, 
    Optional
)
import logging
import socket

logger = logging.getLogger(__name__)
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
    level: Optional[str] = Query(None, description="Filter by log level (INFO, ERROR, WARN)"),
    token_data: dict = Depends(create_jwt_verifier(lambda: PUBLIC_KEY["key"], logger))
):
    user_role = token_data.get("role")
    if user_role != "admin":
        raise_and_log_error(
            logger, 
            status.HTTP_401_UNAUTHORIZED, 
            f"Access denied: user_role={user_role} (admin required)",
        )
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
    response_model=Message,
)
async def health_check():
    if not is_rabbitmq_healthy(RABBITMQ_CONFIG):
        raise_and_log_error(
            logger=logger,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="[LOG:REST] - RabbitMQ not reachable"
        )

    container_id = socket.gethostname()
    logger.debug(f"[LOG:REST] - GET '/health' served by {container_id}")
    return {
        "detail": f"OK - Served by {container_id}",
        "system_metrics": get_system_metrics()
    }
