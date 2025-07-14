import requests
import pandas as pd
import json
import time
import psycopg2
from datetime import datetime, timedelta, timezone
from kafka import KafkaProducer
import os

# PostgreSQL Connection
db_conn = psycopg2.connect(
    dbname = os.environ.get('POSTGRES_DB'),
    user = os.environ.get('POSTGRES_USER'),
    password = os.environ.get('POSTGRES_PASSWORD'),
    host = os.environ.get('POSTGRES_HOST'), #localhost
    port = os.environ.get('POSTGRES_PORT')
)
cursor = db_conn.cursor()

# Kafka Setup
bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
if not bootstrap_servers:
    raise ValueError("❌ Missing KAFKA_BOOTSTRAP_SERVERS environment variable.")

producer = KafkaProducer(
    bootstrap_servers=bootstrap_servers,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
# producer = KafkaProducer(
#     bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"), #'localhost:9092'
#     value_serializer=lambda v: json.dumps(v).encode('utf-8')
# )

# OpenSenseMap Setup
box_id = os.environ.get('BOX_ID')
sensor_id = os.environ.get('SENSOR_ID')
url = f'https://api.opensensemap.org/boxes/{box_id}/data/{sensor_id}'

# Start 60 days ago for full history fetch
last_seen = datetime.now(timezone.utc) - timedelta(days=60)
initial_fetch = True

print("🚀 Ingesting data from OpenSenseMap into PostgreSQL and Kafka...")

try:
    while True:
        from_time = last_seen.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        params = {
            'from-date': from_time,
            'format': 'json',
            'download': 'true'
        }

        try:
            response = requests.get(url, params=params)

            if response.ok:
                data = response.json()

                if isinstance(data, list) and data:
                    df = pd.DataFrame(data)
                    df['createdAt'] = pd.to_datetime(df['createdAt'], utc=True)
                    df = df.sort_values('createdAt')
                    new_df = df[df['createdAt'] > last_seen]

                    for _, row in new_df.iterrows():
                        original_timestamp = row['createdAt']
                        value = float(row['value'])

                        if initial_fetch:
                            # Insert into values table
                            cursor.execute("""
                                INSERT INTO sensor_values (sensor_id, box_id, value, original_timestamp)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (sensor_id, box_id, original_timestamp) DO NOTHING;
                            """, (sensor_id, box_id, value, original_timestamp))
                            db_conn.commit()

                        else:
                            # Create payload
                            payload = {
                                'value': value,
                                'sensor_At': original_timestamp.isoformat(),
                                'sensor_id': sensor_id,
                                'box_id': box_id,
                                'status': 'new event'
                            }

                            # Insert event and retrieve ID
                            cursor.execute("""
                                INSERT INTO sensor_events (event_type, event_data, sensor_id, box_id, status)
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING id;
                            """, (
                                'new_sensor_value',
                                json.dumps(payload),
                                sensor_id,
                                box_id,
                                'new data'
                            ))
                            result = cursor.fetchone()
                            if result is not None:
                                event_id = result[0]
                            else:
                                event_id = None
                            db_conn.commit()
                            
                            # Add event_id to payload
                            payload['event_id'] = event_id
                            
                            # Send to Kafka
                            producer.send('iot-sensor-data', value=payload)
                            print(f"📤 Sent to Kafka: {payload}")

                    if not new_df.empty:
                        last_seen = new_df['createdAt'].max()

                        if initial_fetch:
                            print("✅ Historical data ingested into PostgreSQL.")
                            print(f"📦 Initial data sent to Kafka (nrows: {new_df.shape[0]}).")
                            initial_fetch = False
                        else:
                            print("✅ New data ingested and events dispatched.")

                    else:
                        print("ℹ️ No new data found.")

            else:
                print(f"❌ API error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Exception: {e}")

        time.sleep(60)

except KeyboardInterrupt:
    print("🛑 Gracefully shutting down...")
    cursor.close()
    db_conn.close()
    producer.close()
