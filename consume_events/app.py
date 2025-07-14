import asyncio
import json
import asyncpg
from aiokafka import AIOKafkaConsumer
from datetime import datetime
import os

# Kafka and PostgreSQL config
KAFKA_TOPIC = 'iot-sensor-data'
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
PG_DSN = os.environ.get("PG_DSN") # "postgresql://postgres:postgres@localhost:5432/iot_db"

async def store_value(conn, event):
    try:
        await conn.execute("""
            INSERT INTO sensor_values (box_id, sensor_id, value, original_timestamp, created_at)
            VALUES ($1, $2, $3, $4, $5)
        """,
        event['box_id'],
        event['sensor_id'],
        float(event['value']),
        datetime.fromisoformat(event['sensor_At']),
        datetime.fromisoformat(event['sensor_At']))
        
        # Update event status to 'data consumed'
        await conn.execute("""
            UPDATE sensor_events
            SET status = 'data consumed'
            WHERE id = $1
        """, event['event_id'])
        
        print(f"✅ Stored: {event}")
    except Exception as e:
        print(f"❌ DB error: {e}")

async def consume():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="iot-consumer-group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset="latest"  # consume only new messages
    )

    await consumer.start()
    print("🚀 Kafka consumer started")

    conn = await asyncpg.connect(PG_DSN)

    try:
        async for msg in consumer:
            event = msg.value
            await store_value(conn, event)
    finally:
        await consumer.stop()
        await conn.close()
        print("🛑 Consumer stopped")

if __name__ == "__main__":
    asyncio.run(consume())
