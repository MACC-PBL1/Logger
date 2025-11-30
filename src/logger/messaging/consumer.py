import logging
from ..mongo.database import sync_logs_collection
from chassis.messaging import (
    register_queue_handler,
    MessageType
)
from chassis.consul import ConsulClient 
import requests

logger = logging.getLogger(__name__)
from .global_vars import (
    PUBLIC_KEY,
)

LOGS_QUEUE = "log_aggregation_queue"
LOGS_EXCHANGE = "logs"
LOGS_ROUTING_KEY = "log.#" 


@register_queue_handler(
    queue=LOGS_QUEUE,
    exchange=LOGS_EXCHANGE,
    exchange_type="topic",
    routing_key=LOGS_ROUTING_KEY,
)
def handle_log_message(message: MessageType) -> None:
    try:
        if not isinstance(message, dict):
            logger.warning(f"Received malformed log message: {message}")
            return
        sync_logs_collection.insert_one(message)
    except Exception as e:
        logger.error(f"Failed to insert log into MongoDB: {e}")

LISTENING_QUEUES = {
    "logs": LOGS_QUEUE,
    "public_key": "client.public_key.logger",
}

@register_queue_handler(
    queue=LISTENING_QUEUES["public_key"],
    exchange="public_key",
    exchange_type="fanout"
)
def public_key(message: MessageType) -> None:
    global PUBLIC_KEY
    assert (auth_base_url := ConsulClient(logger).get_service_url("auth")) is not None, (
        "The 'auth' service should be accesible"
    )
    assert "public_key" in message, "'public_key' field should be present."
    assert message["public_key"] == "AVAILABLE", (
        f"'public_key' value is '{message['public_key']}', expected 'AVAILABLE'"
    )
    response = requests.get(f"{auth_base_url}/auth/key", timeout=5)
    assert response.status_code == 200, (
        f"Public key request returned '{response.status_code}', should return '200'"
    )
    data: dict = response.json()
    new_key = data.get("public_key")
    assert new_key is not None, (
        "Auth response did not contain expected 'public_key' field."
    )
    PUBLIC_KEY["key"] = str(new_key)
    logger.info(
        "[EVENT:PUBLIC_KEY:UPDATED] - Public key updated: "
        f"key={PUBLIC_KEY["key"]}"
    )