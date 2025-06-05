import json
from kafka import KafkaConsumer

KAFKA_BROKER = "kafka:9092"  # Use "kafka:9092" if running inside Docker
TOPIC = "forex_event"

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    auto_offset_reset='latest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id="demo-consumer-group"
)

print(f"Listening for messages on topic '{TOPIC}'...")

for message in consumer:
    print("Received message:", message.value)