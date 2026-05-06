import json
from confluent_kafka import Producer

# Connect to the local Kafka broker we just spun up in Docker
conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'fastapi-recipe-producer'
}

producer = Producer(conf)

def delivery_report(err, msg):
    """ Callback to tell us if the message was successfully delivered to Kafka """
    if err is not None:
        print(f"❌ Message delivery failed: {err}")
    else:
        print(f"✅ Event delivered to topic '{msg.topic()}'")

def publish_event(topic: str, event_data: dict):
    """ Converts a Python dictionary to JSON and sends it to Kafka """
    # Trigger any pending delivery reports
    producer.poll(0)
    
    # Send the message asynchronously
    producer.produce(
        topic, 
        value=json.dumps(event_data).encode('utf-8'), 
        callback=delivery_report
    )
    
    # Ensure it gets sent immediately
    producer.flush()