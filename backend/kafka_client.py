import json
from confluent_kafka import Producer
from config import get_settings
from logging_config import logger

settings = get_settings()

producer = None


def get_producer() -> Producer:
    global producer
    if producer is None:
        conf = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": "fastapi-recipe-producer",
        }
        producer = Producer(conf)
        logger.info("Kafka producer initialized")
    return producer


def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Kafka message delivery failed: {err}")
    else:
        logger.info(f"Event delivered to topic '{msg.topic()}'")


def publish_event(topic: str, event_data: dict):
    prod = get_producer()
    prod.poll(0)
    prod.produce(
        topic,
        value=json.dumps(event_data).encode("utf-8"),
        callback=delivery_report,
    )
    prod.flush()
