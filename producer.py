import json
import time
import requests
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

API_URL = "https://api.exchangerate.host/live?access_key=24350d1a3226aad12b9e47f7fe2fc424"
KAFKA_BROKER = "localhost:29092" 
TOPIC = "forex_event"

for _ in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        break
    except NoBrokersAvailable:
        print("Kafka broker not available, retrying in 5 seconds...")
        time.sleep(5)
else:
    raise Exception("Kafka broker not available after multiple attempts.")

def fetch_and_send():
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    base_currency = data.get("source")
    timestamp = data.get("timestamp")
    quotes = data.get("quotes", {})
    for quote, rate in quotes.items():
        # Remove the base currency prefix (e.g., USDJPY -> JPY)
        quote_currency = quote[len(base_currency):]
        message = {
            "base_currency": base_currency,
            "quote_currency": quote_currency,
            "exchange_rate": rate,
            "timestamp": timestamp
        }
        producer.send(TOPIC, value=message)
        print(f"Sent: {message}")

if __name__ == "__main__":
    while True:
        fetch_and_send()
        time.sleep(150)  