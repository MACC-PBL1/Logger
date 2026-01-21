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
    Optional,
    Dict,
    Any
)
import logging
import socket

from datetime import datetime
from fastapi import Query

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

# ENDPOINTS PARA VISUALIZACION GRAFANA
@Router.get(
    "/public",
    response_model=List[LogEntry],
    summary="Public logs endpoint (read-only)",
    description="Public endpoint for observability tools (Grafana). Read-only access."
)
async def get_logs_public(
    limit: int = Query(100, ge=1, le=500),
    log_type: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
):
    mongo_query: Dict[str, Any] = {}

    if log_type:
        mongo_query["log_type"] = log_type
    if level:
        mongo_query["level"] = level
    if service:
        mongo_query["service"] = service

    if from_ts or to_ts:
        mongo_query["timestamp"] = {}
        if from_ts:
            mongo_query["timestamp"]["$gte"] = from_ts
        if to_ts:
            mongo_query["timestamp"]["$lte"] = to_ts

    projection = {
        "_id": 0,
        "function": 0,
        "host": 0,
        "module": 0,
        "routing_key": 0,
        "service": 0
    }

    cursor = (
        logs_collection
        .find(mongo_query, projection)
        .sort("timestamp", -1)
        .limit(limit)
    )

    results: list = []
    async for document in cursor:
        if "timestamp" in document:
            ts = document["timestamp"]

            if isinstance(ts, datetime):
                document["timestamp"] = ts.isoformat().replace("+00:00", "Z")
            elif isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    document["timestamp"] = dt.isoformat().replace("+00:00", "Z")
                except Exception:
                    document["timestamp"] = ts.replace(" ", "T").replace("+00:00", "Z")

        results.append(document)

    return results


@Router.get(
    "/stats/levels",
    summary="Logs count grouped by level (for Grafana)"
)
async def logs_by_level(
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
):
    match: Dict[str, Any] = {}

    if from_ts or to_ts:
        match["timestamp"] = {}
        if from_ts:
            match["timestamp"]["$gte"] = from_ts
        if to_ts:
            match["timestamp"]["$lte"] = to_ts

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$level",
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "level": "$_id",
                "count": 1
            }
        }
    ]

    cursor = logs_collection.aggregate(pipeline)
    return [doc async for doc in cursor]


@Router.get(
    "/stats/loggers",
    summary="Logs count grouped by logger"
)
async def logs_by_logger():
    pipeline = [
        {
            "$match": {
                "source.logger": {"$exists": True, "$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$source.logger",
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "logger": "$_id",
                "count": 1
            }
        }
    ]

    cursor = logs_collection.aggregate(pipeline)
    return [doc async for doc in cursor]

@Router.get(
    "/stats/subtypes",
    summary="Logs count grouped by subtype (service)"
)
async def logs_by_subtype(
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
):
    match: Dict[str, Any] = {}

    if from_ts or to_ts:
        match["timestamp"] = {}
        if from_ts:
            match["timestamp"]["$gte"] = from_ts
        if to_ts:
            match["timestamp"]["$lte"] = to_ts

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": "$subtype",
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "subtype": "$_id",
                "count": 1
            }
        },
        {"$sort": {"count": -1}}
    ]

    cursor = logs_collection.aggregate(pipeline)
    return [doc async for doc in cursor]


@Router.get(
    "/stats/timeline",
    summary="Logs count over time (grouped by intervals)"
)
async def logs_timeline(
    interval: str = Query("5m", description="Time interval: 1m, 5m, 15m, 1h, 1d"),
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
):

    match: Dict[str, Any] = {}

    if from_ts or to_ts:
        match["timestamp"] = {}
        if from_ts:
            match["timestamp"]["$gte"] = from_ts.isoformat().replace("+00:00", "Z")
        if to_ts:
            match["timestamp"]["$lte"] = to_ts.isoformat().replace("+00:00", "Z")

    # Mapeo de intervalos a milisegundos
    interval_ms = {
        "1m": 60000,        
        "5m": 300000,      
        "15m": 900000,     
        "1h": 3600000,     
        "1d": 86400000     
    }
    
    bucket_size = interval_ms.get(interval, 300000)

    pipeline = [
        {"$match": match},
        {
            # Convertir string timestamp a Date
            "$addFields": {
                "timestamp_date": {
                    "$dateFromString": {
                        "dateString": "$timestamp",
                        "onError": None,
                        "onNull": None
                    }
                }
            }
        },
        {
            # Filtrar documentos donde la conversión falló
            "$match": {
                "timestamp_date": {"$ne": None}
            }
        },
        {
            # Agrupar por intervalos y por level
            "$group": {
                "_id": {
                    "bucket": {
                        "$dateTrunc": {
                            "date": "$timestamp_date",
                            "unit": "minute" if interval in ["1m", "5m", "15m"] else ("hour" if interval == "1h" else "day"),
                            "binSize": 5 if interval == "5m" else (15 if interval == "15m" else 1)
                        }
                    },
                    "level": "$level"
                },
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "timestamp": "$_id.bucket",
                "level": "$_id.level",
                "count": 1
            }
        },
        {"$sort": {"timestamp": 1, "level": 1}}
    ]

    try:
        cursor = logs_collection.aggregate(pipeline)
        results = [doc async for doc in cursor]

        for doc in results:
            if isinstance(doc["timestamp"], datetime):
                doc["timestamp"] = doc["timestamp"].isoformat().replace("+00:00", "Z")
        
        return results
    except Exception as e:
        logger.error(f"Error in timeline aggregation: {e}")
        return []