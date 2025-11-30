import logging
from ..mongo.database import sync_logs_collection
from chassis.messaging import (
    register_queue_handler,
    MessageType
)

logger = logging.getLogger(__name__)


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