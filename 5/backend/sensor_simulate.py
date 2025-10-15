import asyncio
import json
import random
import ssl
from asyncio_mqtt import Client, MqttError

# HiveMQ Cloud config
MQTT_BROKER = "d736eed424d94cb397ff3f5fa9615a2d.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "anuragnitw6"
MQTT_PASSWORD = "1234"

SHIP_ID = "MTGREATMANTA"
TANK_ID = 1
SENSORS = ["SN-G-001", "CO-L-23B", "S3"]
PUBLISH_TOPIC = f"ship/{SHIP_ID}/sensors"
INTERVAL_SEC = 3

# Random walk state
_state = {
    sid: {"O2": 20.9, "CO": 8.0, "LEL": 2.0, "H2S": 2.0} for sid in SENSORS
}

def _clamp(v, lo=None, hi=None):
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return v

def _tick_sensor(prev):
    o2  = _clamp(prev["O2"] + (random.random() - 0.5) * 0.2, 14.0, 21.0)
    co  = _clamp(prev["CO"] + (random.random() - 0.5) * 4.0, 0.0, 200.0)
    lel = _clamp(prev["LEL"] + (random.random() - 0.5) * 0.7, 0.0, 100.0)
    h2s = _clamp(prev["H2S"] + (random.random() - 0.5) * 0.7, 0.0, 100.0)
    return {"O2": o2, "CO": co, "LEL": lel, "H2S": h2s}

async def publish_sensor_data():
    ssl_context = ssl.create_default_context()
    try:
        async with Client(
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD,
            tls_context=ssl_context
        ) as client:
            while True:
                readings = []
                for sid in SENSORS:
                    _state[sid] = _tick_sensor(_state[sid])
                    readings.append({"sensor_id": sid, **_state[sid]})
                payload = json.dumps({"tank_id": TANK_ID, "readings": readings})
                try:
                    await client.publish(PUBLISH_TOPIC, payload, qos=1)
                    print(f"Sent: {payload}")
                except MqttError as e:
                    print(f"Publish failed: {e}")
                await asyncio.sleep(INTERVAL_SEC)
    except MqttError as e:
        print(f"MQTT connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(publish_sensor_data())
