import logging
from ..mongo.database import sync_logs_collection
from chassis.messaging import (
    register_queue_handler,
    MessageType
)

logger = logging.getLogger(__name__)


QUEUE_NAME = "log_aggregation_queue"
EXCHANGE_NAME = "logs"
ROUTING_KEY = "log.#"

@register_queue_handler(
    queue=QUEUE_NAME,
    exchange=EXCHANGE_NAME,
    exchange_type="topic",
    routing_key=ROUTING_KEY,
)
def handle_log_message(message: MessageType) -> None:
    if "log_type" not in message or "message" not in message:
        logger.warning(f"Message had incorrect format {message}")
        return

    result = sync_logs_collection.insert_one(message)



LISTENING_QUEUES = {
    "logs": QUEUE_NAME
}