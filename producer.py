import json, time, requests
from kafka import KafkaProducer
from datetime import datetime

KAFKA_BROKER = "kafka:9092"
TOPIC = "forex_event"

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

while True:
    resp = requests.get("https://api.exchangerate.host/live?access_key=5d6f42103c15bbe91d8a473fbaa967d5", timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    base = payload["source"]
    ts = payload["timestamp"]
    quotes = payload["quotes"]
    for pair, rate in quotes.items():
        quote = pair[len(base):] if pair.startswith(base) else pair
        record = {
            "base_currency": base,
            "quote_currency": quote,
            "exchange_rate": rate,
            "timestamp": ts
        }
        producer.send(TOPIC, record)

    producer.flush()
    time.sleep(60)  # Adjust the sleep time as needed