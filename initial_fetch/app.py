import requests
import pandas as pd
import time
import psycopg2
import os
import sys
from datetime import datetime, timedelta, timezone

# PostgreSQL Connection
db_conn = psycopg2.connect(
    dbname=os.environ.get('POSTGRES_DB'),
    user=os.environ.get('POSTGRES_USER'),
    password=os.environ.get('POSTGRES_PASSWORD'),
    host=os.environ.get('POSTGRES_HOST'),
    port=os.environ.get('POSTGRES_PORT')
)
cursor = db_conn.cursor()

# OpenSenseMap Setup
box_id = os.environ.get('BOX_ID')
sensor_id = os.environ.get('SENSOR_ID')
url = f'https://api.opensensemap.org/boxes/{box_id}/data/{sensor_id}'


# Start 60 days ago
last_seen = datetime.now(timezone.utc) - timedelta(days=60)
print("🚀 Starting historical ingestion...")


# ✅ Check if historical data already exists
cursor.execute("SELECT COUNT(*) FROM sensor_values;")
result = cursor.fetchone()
count = result[0] if result is not None else 0

if count > 0:
    print(f"🚫 Historical data already exists in sensor_values (count: {count}). Skipping ingestion.")
    cursor.close()
    db_conn.close()
    sys.exit(0)  # Exit cleanly
else:
    print("✅ No historical data found. Proceeding with ingestion.")

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

                            cursor.execute("""
                                    INSERT INTO sensor_values (sensor_id, box_id, value, original_timestamp)
                                    VALUES (%s, %s, %s, %s)
                                    ON CONFLICT (sensor_id, box_id, original_timestamp) DO NOTHING;
                                """, (sensor_id, box_id, value, original_timestamp))
                            db_conn.commit()

                        if not new_df.empty:
                            last_seen = new_df['createdAt'].max()
                            print(f"📥 Ingested {new_df.shape[0]} new rows. Last seen: {last_seen}")
                        else:
                            print("✅ Historical data ingestion complete.")
                            with open("/tmp/history_ingested.flag", "w") as f:
                                f.write("done")
                            break  # exit loop
                    else:
                        print("✅ No more historical data found.")
                        with open("/tmp/history_ingested.flag", "w") as f:
                            f.write("done")
                        break

                else:
                    print(f"❌ API error: {response.status_code} - {response.text}")
                    time.sleep(100)

            except Exception as e:
                print(f"❌ Exception: {e}")
                time.sleep(100)

    except KeyboardInterrupt:
        print("🛑 Interrupted.")

    finally:
        cursor.close()
        db_conn.close()
        print("🔌 Database connection closed.")
