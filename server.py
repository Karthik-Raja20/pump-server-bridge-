import json
import os
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template_string

# ── Configuration (override via environment variables on Render) ──────────
MQTT_BROKER = os.environ.get("MQTT_BROKER", "35.202.96.47")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "AG_201/Test")
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "device_001")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "Karthik_001")

app = Flask(__name__)

# ── Shared in-memory state (the "mailbox") ─────────────────────────────────
state = {
    "payload": None,          # last parsed JSON dict from the device
    "raw": None,              # last raw MQTT message string (fallback if not JSON)
    "received_at": None,      # UTC ISO timestamp of last message
    "connected": False,       # current MQTT connection status
    "message_count": 0,       # total messages received since server start
}
state_lock = threading.Lock()


# ── MQTT background client ─────────────────────────────────────────────────
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[mqtt] connected to {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[mqtt] subscribed to topic '{MQTT_TOPIC}'")
        with state_lock:
            state["connected"] = True
    else:
        print(f"[mqtt] connect failed, reason code {reason_code}")


def on_disconnect(client, userdata, reason_code, properties=None):
    print(f"[mqtt] disconnected, reason code {reason_code}")
    with state_lock:
        state["connected"] = False


def on_message(client, userdata, msg):
    raw = msg.payload.decode("utf-8", errors="replace")
    parsed = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        pass  # keep raw only, e.g. if the device sends non-JSON text

    with state_lock:
        state["raw"] = raw
        state["payload"] = parsed
        state["received_at"] = datetime.now(timezone.utc).isoformat()
        state["message_count"] += 1


def start_mqtt_thread():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_forever()  # blocks; reconnects are handled by the retry loop below
        except Exception as exc:
            print(f"[mqtt] connection error: {exc}, retrying in 5s")
            with state_lock:
                state["connected"] = False
            time.sleep(5)


# Start the MQTT subscriber as soon as the module loads, in its own thread,
# so it runs alongside Flask's web server inside the same process/service.
mqtt_thread = threading.Thread(target=start_mqtt_thread, daemon=True)
mqtt_thread.start()


# ── HTTP routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "service": "mqtt-http-bridge",
        "topic": MQTT_TOPIC,
        "broker": f"{MQTT_BROKER}:{MQTT_PORT}",
        "routes": ["/data", "/dashboard"],
    })


@app.route("/data")
def get_data():
    with state_lock:
        snapshot = dict(state)
    return jsonify(snapshot)


@app.route("/dashboard")
def dashboard():
    return render_template_string(DASHBOARD_HTML, topic=MQTT_TOPIC, broker=MQTT_BROKER)


# ── Dashboard page (self-contained: HTML + CSS + JS in one string) ────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AG-201 · Live Readout</title>
<style>
  :root {
    --bg: #10151a;
    --panel: #1a2129;
    --panel-border: #2a333d;
    --text: #e7ecf0;
    --muted: #7c8894;
    --accent: #35c6b0;
    --accent-dim: #1f4a44;
    --alarm: #e2585f;
    --font-ui: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    --font-num: "IBM Plex Mono", "SF Mono", "Roboto Mono", Consolas, monospace;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-ui);
    padding: 32px 20px 60px;
  }
  .wrap { max-width: 920px; margin: 0 auto; }

  header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 16px;
    border-bottom: 1px solid var(--panel-border);
    padding-bottom: 20px;
    margin-bottom: 28px;
  }
  h1 {
    font-size: 22px;
    font-weight: 600;
    margin: 0 0 6px;
    letter-spacing: 0.2px;
  }
  .meta {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.6;
  }
  .meta code { color: var(--text); font-family: var(--font-num); }

  .status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--muted);
  }
  .dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--alarm);
    transition: background 0.3s ease;
  }
  .dot.live { background: var(--accent); box-shadow: 0 0 0 4px var(--accent-dim); }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 14px;
  }
  .card {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 6px;
    padding: 18px 20px;
  }
  .card .label {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 10px;
  }
  .card .value {
    font-family: var(--font-num);
    font-size: 30px;
    font-variant-numeric: tabular-nums;
    color: var(--text);
  }
  .card .unit {
    font-size: 14px;
    color: var(--muted);
    margin-left: 4px;
  }

  .footer {
    margin-top: 28px;
    font-size: 12px;
    color: var(--muted);
  }
  .empty {
    color: var(--muted);
    font-size: 14px;
    padding: 40px 0;
    text-align: center;
  }
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <h1>AG-201 Live Read-out</h1>
        <div class="meta">
          topic <code>{{ topic }}</code> &nbsp;·&nbsp; broker <code>{{ broker }}</code>
        </div>
      </div>
      <div class="status">
        <span class="dot" id="statusDot"></span>
        <span id="statusText">connecting…</span>
      </div>
    </header>

    <div class="grid" id="grid"></div>
    <div class="empty" id="emptyMsg" style="display:none;">No message received yet from the device.</div>

    <div class="footer" id="footer"></div>
  </div>

<script>
  const grid = document.getElementById('grid');
  const emptyMsg = document.getElementById('emptyMsg');
  const footer = document.getElementById('footer');
  const dot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');

  function labelize(key) {
    return key.replace(/_/g, ' ').replace(/beetween/i, 'between').toLowerCase();
  }

  function unitFor(key) {
    if (/voltage/i.test(key)) return 'V';
    if (/current/i.test(key)) return 'A';
    return '';
  }

  async function refresh() {
    try {
      const res = await fetch('/data', { cache: 'no-store' });
      const data = await res.json();

      dot.classList.toggle('live', !!data.connected);
      statusText.textContent = data.connected ? 'connected to broker' : 'disconnected from broker';

      if (!data.payload) {
        grid.innerHTML = '';
        emptyMsg.style.display = 'block';
      } else {
        emptyMsg.style.display = 'none';
        grid.innerHTML = Object.entries(data.payload)
          .filter(([k]) => k !== 'timestamp')
          .map(([k, v]) => `
            <div class="card">
              <div class="label">${labelize(k)}</div>
              <div class="value">${v}<span class="unit">${unitFor(k)}</span></div>
            </div>
          `).join('');
      }

      const received = data.received_at ? new Date(data.received_at).toLocaleTimeString() : '—';
      footer.textContent = `Last message: ${received} · Total messages received: ${data.message_count}`;
    } catch (err) {
      statusText.textContent = 'bridge unreachable';
      dot.classList.remove('live');
    }
  }

  refresh();
  setInterval(refresh, 2000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
