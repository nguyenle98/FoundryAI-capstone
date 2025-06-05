import os
import json
import time
import logging

from kafka import KafkaConsumer
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector.errors import ProgrammingError

# ── CONFIGURATION ──────────────────────────────────────────────────────────────

# Kafka settings (fallback to “kafka:9092” if not provided in env)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "forex_event")
GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP", "forex-consumer-group")

# How many times to retry Snowflake inserts or Kafka connection
MAX_RETRIES = 3

# ── LOGGING SETUP ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
)
logger = logging.getLogger("forex_consumer")


# ── SNOWFLAKE WRAPPER ────────────────────────────────────────────────────────────
class SnowflakeDB:
    def __init__(self):
        # Explicitly load from “secret.env” (not “.env”)
        load_dotenv("secret.env")

        # Pull credentials from environment
        user = os.getenv("SNOWFLAKE_USER")
        pwd = os.getenv("SNOWFLAKE_PASSWORD")
        acct = os.getenv("SNOWFLAKE_ACCOUNT")
        wh = os.getenv("SNOWFLAKE_WAREHOUSE")
        db = os.getenv("SNOWFLAKE_DATABASE")
        schema = os.getenv("SNOWFLAKE_SCHEMA")
        role = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")

        if not all([user, pwd, acct, wh, db, schema]):
            logger.error("Missing one or more Snowflake environment variables.")
            raise RuntimeError("Snowflake credentials incomplete in environment.")

        try:
            self.conn = snowflake.connector.connect(
                user=user,
                password=pwd,
                account=acct,
                warehouse=wh,
                database=db,
                schema=schema,
                role=role
            )
            logger.info("✅ Connected to Snowflake.")
        except Exception as e:
            logger.exception("❌ Failed to connect to Snowflake:")
            raise

    def insert_rate(
        self,
        base_currency: str,
        quote_currency: str,
        exchange_rate: float,
        event_time,
    ):
        """
        INSERT INTO CAPSTONE.SC_LAB_M1W4_BRONZE.RAW_KAFKA_EVENTS
        (BASE_CURRENCY, QUOTE_CURRENCY, EXCHANGE_RATE, EVENT_TIME)
        VALUES (%s, %s, %s, %s)
        """
        sql = """
        INSERT INTO CAPSTONE.SC_LAB_M1W4_BRONZE.RAW_KAFKA_EVENTS
        (BASE_CURRENCY, QUOTE_CURRENCY, EXCHANGE_RATE, EVENT_TIME)
        VALUES (%s, %s, %s, %s)
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        base_currency,
                        quote_currency,
                        exchange_rate,
                        event_time,
                    ),
                )
        except ProgrammingError as pe:
            # e.g. type mismatch, permission error, etc.
            logger.exception("❌ ProgrammingError when inserting into Snowflake:")
            raise
        except Exception as e:
            logger.exception("❌ Unexpected error when inserting into Snowflake:")
            raise

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
                logger.info("🔒 Snowflake connection closed.")
            except Exception:
                logger.exception("Error while closing Snowflake connection.")


# ── MESSAGE PROCESSING ──────────────────────────────────────────────────────────
def process_message(msg_value: dict, db: SnowflakeDB, retry: int = 0) -> bool:
    """
    Write a single Kafka message into Snowflake, with up to MAX_RETRIES.
    msg_value is expected to look like:
      {
        "base_currency": "USD",
        "quote_currency": "AED",
        "exchange_rate": 3.67291,
        "timestamp": 1749023055
      }
    """
    try:
        base = msg_value.get("base_currency")
        quote = msg_value.get("quote_currency")
        rate = float(msg_value.get("exchange_rate"))
        ts_epoch = int(msg_value.get("timestamp"))

        # Convert Unix epoch seconds → Python datetime
        from datetime import datetime
        event_time = datetime.fromtimestamp(ts_epoch)

        db.insert_rate(base, quote, rate, event_time)
        return True

    except Exception as e:
        if retry < MAX_RETRIES:
            delay = 2 ** retry
            logger.warning(
                f"⚠️ Error inserting message into Snowflake "
                f"(attempt {retry+1}/{MAX_RETRIES}); retrying in {delay}s..."
            )
            time.sleep(delay)
            return process_message(msg_value, db, retry + 1)
        else:
            logger.error(f"❌ Permanently failed to insert message: {msg_value}")
            return False


# ── KAFKA CONSUMER + MAIN LOOP ───────────────────────────────────────────────────
def main():
    # 1) Initialize KafkaConsumer (retry up to 5×, 5s between attempts)
    consumer = None
    for attempt in range(5):
        try:
            consumer = KafkaConsumer(
                TOPIC_NAME,
                bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
                group_id=GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
            )
            logger.info(f"🎧 KafkaConsumer connected, subscribed to topic: {TOPIC_NAME}")
            break
        except Exception:
            logger.warning(f"⚠️ Kafka not ready (attempt {attempt+1}/5). Retrying in 5 s…")
            time.sleep(5)

    if consumer is None:
        logger.error("❌ Could not initialize KafkaConsumer after multiple retries.")
        return

    # 2) Initialize Snowflake connection
    try:
        db = SnowflakeDB()
    except Exception:
        return

    # 3) Consume forever
    logger.info("▶️  Waiting for new messages…")
    try:
        for message in consumer:
            # message.value is already a dict, thanks to value_deserializer
            msg = message.value
            offset = message.offset
            partition = message.partition
            timestamp = message.timestamp  # Kafka’s timestamp in ms

            logger.info(
                f"📥 Received message at offset {offset}, partition {partition}, kafka_ts={timestamp}"
            )
            success = process_message(msg, db)
            if success:
                logger.info("✅ Inserted successfully into Snowflake.")
            else:
                logger.warning("⚠️ Skipping this message after retries.")
    except KeyboardInterrupt:
        logger.info("⏹️ Interrupted by user; shutting down.")
    except Exception:
        logger.exception("🛑 Fatal error in consuming loop.")
    finally:
        consumer.close()
        logger.info("🔒 KafkaConsumer closed.")
        db.close()


if __name__ == "__main__":
    main()