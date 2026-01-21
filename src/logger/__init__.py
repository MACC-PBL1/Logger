from contextlib import asynccontextmanager
from fastapi import FastAPI
from hypercorn.asyncio import serve
from hypercorn.config import Config
from threading import Thread
import asyncio
import os
import logging.config
from chassis.consul import CONSUL_CLIENT 

from chassis.messaging import (
    start_rabbitmq_listener
)

from .messaging.consumer import LISTENING_QUEUES
from .routers import Router

from .messaging.global_vars import (
    RABBITMQ_CONFIG,
)

logger = logging.getLogger("log_aggregation")

@asynccontextmanager
async def lifespan(__app: FastAPI):
    try:
        logger.info("Starting Log Aggregation Service")
        
        logger.info("Starting RabbitMQ consumers...")
        try:
            for _, queue_name in LISTENING_QUEUES.items():
                Thread(
                    target=start_rabbitmq_listener,
                    args=(queue_name, RABBITMQ_CONFIG),
                    daemon=True,
                ).start()
        except Exception as e:
            logger.error(f"Could not start RabbitMQ listeners: {e}")
        logger.info("[LOG:AUTH] - Registering service to Consul...")
        try:
            CONSUL_CLIENT.register_service(
                service_name="auth",
                ec2_address=os.getenv("HOST_IP", "localhost"),
                service_port=int(os.getenv("HOST_PORT", 80)),
            )
        except Exception as e:
            logger.error(f"[LOG:AUTH] - Failed to register with Consul: Reason={e}", exc_info=True)
        yield
    finally:
        logger.info("Shutting down Log Aggregation Service")
        CONSUL_CLIENT.deregister_service()

# Información de la App
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DESCRIPTION = """
Centralized Log Aggregation Service backed by MongoDB.
Consumes logs from RabbitMQ 'logs' exchange and exposes them via REST API.
"""

APP = FastAPI(
    title="Log Aggregation Service",
    description=DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)

APP.include_router(Router)

def start_server():
    config = Config()
    config.bind = [os.getenv("HOST", "0.0.0.0") + ":" + os.getenv("PORT", "8000")]
    config.workers = int(os.getenv("WORKERS", "1"))
    
    logger.info("Starting Hypercorn server on %s", config.bind)
    asyncio.run(serve(APP, config)) # type: ignore