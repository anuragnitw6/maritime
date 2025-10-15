# sensor_simulator_async.py — multi-sensor, per-tank payload (async version)

import asyncio
import json
import random
from asyncio_mqtt import Client, MqttError

# --------- Config ---------
MQTT_BROKER = "d736eed424d94cb397ff3f5fa9615a2d.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "anuragnitw6"
MQTT_PASSWORD = "1234"

SHIP_ID = "MTGREATMANTA"   # must match a real ship id in your DB
TANK_ID = 1                 # existing tank id

# Simulate these sensors inside the tank
SENSORS = ["SN-G-001", "CO-L-23B", "S3"]

PUBLISH_TOPIC = f"ship/{SHIP_ID}/sensors"
INTERVAL_SEC = 3

# Starting baselines (per sensor) and step magnitudes
O2_BASE,  O2_STEP  = 20.9, 0.20
CO_BASE,  CO_STEP  = 8.0,  4.0
LEL_BASE, LEL_STEP = 2.0,  0.7
H2S_BASE, H2S_STEP = 2.0,  0.7

# 10% chance per tick to spike CO to a dangerous level for one random sensor
DANGER_PROB = 0.10
CO_DANGER_SPIKE = 110.0

# --------- Simulation state ---------
_state = {
    sid: {
        "O2":  O2_BASE + random.uniform(-0.2, 0.2),
        "CO":  CO_BASE + random.uniform(-2, 2),
        "LEL": LEL_BASE + random.uniform(-0.5, 0.5),
        "H2S": H2S_BASE + random.uniform(-0.5, 0.5),
    }
    for sid in SENSORS
}

def _clamp(v, lo=None, hi=None):
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return v

def _tick_sensor(prev):
    """do one random-walk tick for a single sensor"""
    o2  = prev["O2"]  + (random.random() - 0.5) * O2_STEP
    co  = prev["CO"]  + (random.random() - 0.5) * CO_STEP
    lel = prev["LEL"] + (random.random() - 0.5) * LEL_STEP
    h2s = prev["H2S"] + (random.random() - 0.5) * H2S_STEP

    # clamp to sane ranges
    o2  = _clamp(o2, 14.0, 21.0)
    co  = _clamp(co, 0.0, 200.0)
    lel = _clamp(lel, 0.0, 100.0)
    h2s = _clamp(h2s, 0.0, 100.0)

    return {"O2": o2, "CO": co, "LEL": lel, "H2S": h2s}

async def publish_sensor_data():
    """async loop to simulate and publish sensor data"""
    try:
        async with Client(
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD,
            tls_context=True
        ) as client:

            tick = 0
            while True:
                tick += 1

                spiked_sensor = None
                if random.random() < DANGER_PROB:
                    spiked_sensor = random.choice(SENSORS)

                readings = []
                for sid in SENSORS:
                    # random walk
                    _state[sid] = _tick_sensor(_state[sid])

                    # optional spike
                    if sid == spiked_sensor:
                        print(f">>> SIMULATING DANGER EVENT on {sid}! CO spike!")
                        _state[sid]["CO"] = CO_DANGER_SPIKE

                    # snapshot & round
                    o2  = round(_state[sid]["O2"],  2)
                    co  = round(_state[sid]["CO"],  2)
                    lel = round(_state[sid]["LEL"], 2)
                    h2s = round(_state[sid]["H2S"], 2)

                    readings.append({"sensor_id": sid, "O2": o2, "CO": co, "LEL": lel, "H2S": h2s})

                    # relax CO after spike
                    if _state[sid]["CO"] > 100:
                        _state[sid]["CO"] = CO_BASE

                payload = json.dumps({"tank_id": TANK_ID, "readings": readings})

                try:
                    await client.publish(PUBLISH_TOPIC, payload, qos=1)
                    print(f"Sent {payload} -> {PUBLISH_TOPIC}")
                except MqttError as e:
                    print(f"Failed to send message to topic {PUBLISH_TOPIC}: {e}")

                await asyncio.sleep(INTERVAL_SEC)

    except MqttError as e:
        print(f"MQTT connection failed: {e}")


# ---------- Optional standalone run ----------
if __name__ == '__main__':
    asyncio.run(publish_sensor_data())
