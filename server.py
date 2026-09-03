from flask import Flask, request, Response

app = Flask(__name__)

# The "mailbox" — always holds ONLY the latest packet.
latest_packet = ""


@app.route("/")
def home():
    return "Server is running. POST to /data to send data, GET /data to read the latest packet, or visit /dashboard."


@app.route("/data", methods=["POST"])
def receive_data():
    global latest_packet
    latest_packet = request.get_data(as_text=True)
    return {"status": "ok", "received_length": len(latest_packet)}, 200


@app.route("/data", methods=["GET"])
def send_data():
    return Response(latest_packet, mimetype="text/plain")


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Live Dashboard</title>
<style>
  :root{
    --bg:#eef1f5;
    --border:#e1e5eb;
    --text:#111827;
    --muted:#6b7280;
    --red:#e5484d;
    --yellow:#f5a524;
    --blue:#3b82f6;
    --teal:#0f9488;
    --green:#16a34a;
    --amber:#f59e0b;
  }
  *{box-sizing:border-box;}
  body{
    margin:0;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background:var(--bg);
    color:var(--text);
    padding:32px;
  }
  header{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    margin-bottom:24px;
  }
  h1{font-size:22px;margin:0 0 4px 0;}
  .sub{color:var(--muted);font-size:13px;}
  button.report{
    background:var(--teal);
    color:#fff;
    border:none;
    padding:10px 18px;
    border-radius:8px;
    font-size:14px;
    cursor:pointer;
  }
  section{
    background:#fff;
    border:1px solid var(--border);
    border-radius:12px;
    padding:20px;
    margin-bottom:20px;
  }
  .section-title{
    font-size:12px;
    letter-spacing:.05em;
    text-transform:uppercase;
    color:var(--muted);
    margin-bottom:14px;
    font-weight:600;
  }
  .row{display:flex;gap:16px;flex-wrap:wrap;}
  .card{
    flex:1;
    min-width:160px;
    background:#fff;
    border:1px solid var(--border);
    border-radius:10px;
    padding:16px;
  }
  .card.accent{border-left:4px solid var(--teal);}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;}
  .label{font-size:12px;color:var(--muted);font-weight:600;margin-bottom:8px;display:flex;align-items:center;}
  .value{font-size:26px;font-weight:700;}
  .unit{font-size:13px;color:var(--muted);font-weight:500;margin-left:2px;}
  .raw{font-size:12px;color:var(--muted);margin-top:4px;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px;}
  @media (max-width:800px){.grid2{grid-template-columns:1fr;}}
</style>
</head>
<body>
<header>
  <div>
    <h1>Live Dashboard</h1>
    <div class="sub">Real-time protection status &middot; Updated <span id="ago">--</span></div>
  </div>
  <button class="report" onclick="generateReport()">Generate Report</button>
</header>

<div class="grid2">
  <section>
    <div class="section-title">Voltage (R-Y-B)</div>
    <div class="row">
      <div class="card">
        <div class="label"><span class="dot" style="background:var(--red)"></span><span class="dot" style="background:var(--yellow)"></span>Voltage R-Y</div>
        <div class="value" id="v-ry">--<span class="unit">V</span></div>
      </div>
      <div class="card">
        <div class="label"><span class="dot" style="background:var(--yellow)"></span><span class="dot" style="background:var(--blue)"></span>Voltage Y-B</div>
        <div class="value" id="v-yb">--<span class="unit">V</span></div>
      </div>
      <div class="card">
        <div class="label"><span class="dot" style="background:var(--blue)"></span><span class="dot" style="background:var(--red)"></span>Voltage B-R</div>
        <div class="value" id="v-br">--<span class="unit">V</span></div>
      </div>
    </div>
  </section>

  <section>
    <div class="section-title">Current (R-Y-B)</div>
    <div class="row">
      <div class="card">
        <div class="label"><span class="dot" style="background:var(--red)"></span>Current R Phase</div>
        <div class="value" id="i-r">--<span class="unit">A</span></div>
      </div>
      <div class="card">
        <div class="label"><span class="dot" style="background:var(--yellow)"></span>Current Y Phase</div>
        <div class="value" id="i-y">--<span class="unit">A</span></div>
      </div>
      <div class="card">
        <div class="label"><span class="dot" style="background:var(--blue)"></span>Current B Phase</div>
        <div class="value" id="i-b">--<span class="unit">A</span></div>
      </div>
    </div>
  </section>
</div>

<div class="grid2">
  <section>
    <div class="section-title">Overload &amp; Dry Run Thresholds</div>
    <div class="row">
      <div class="card">
        <div class="label">Set Current Pump 1</div>
        <div class="value" id="th-p1">--<span class="unit">A</span></div>
      </div>
      <div class="card">
        <div class="label">Set Current Pump 2</div>
        <div class="value" id="th-p2">--<span class="unit">A</span></div>
      </div>
      <div class="card">
        <div class="label">Set Dry-Run Current</div>
        <div class="value" id="th-dry">--<span class="unit">%</span></div>
      </div>
    </div>
  </section>

  <section>
    <div class="section-title">Ton / Toff Timers</div>
    <div class="row">
      <div class="card">
        <div class="label">Set On Time</div>
        <div class="value" id="t-on">--<span class="unit">min</span></div>
      </div>
      <div class="card">
        <div class="label">Set Off Time</div>
        <div class="value" id="t-off">--<span class="unit">min</span></div>
      </div>
    </div>
  </section>
</div>

<div class="grid2">
  <section>
    <div class="section-title">System Control</div>
    <div class="row">
      <div class="card accent" style="border-left-color:var(--teal)">
        <div class="label">Active Pump</div>
        <div class="value" id="sys-pump" style="color:var(--teal)">--</div>
        <div class="raw" id="sys-pump-raw"></div>
      </div>
      <div class="card accent" style="border-left-color:var(--green)">
        <div class="label">Mode</div>
        <div class="value" id="sys-mode" style="color:var(--green)">--</div>
        <div class="raw" id="sys-mode-raw"></div>
      </div>
      <div class="card">
        <div class="label">Pump State</div>
        <div class="value" id="sys-state">--</div>
        <div class="raw" id="sys-state-raw"></div>
      </div>
    </div>
  </section>

  <section>
    <div class="section-title">Tank Levels</div>
    <div class="row">
      <div class="card" id="tank-bottom-card">
        <div class="label">Bottom Tank</div>
        <div class="value" id="tank-bottom">--</div>
        <div class="raw" id="tank-bottom-raw"></div>
      </div>
      <div class="card" id="tank-top-card">
        <div class="label">Top Tank</div>
        <div class="value" id="tank-top">--</div>
        <div class="raw" id="tank-top-raw"></div>
      </div>
    </div>
  </section>
</div>

<script>
let lastValues = null;
let lastUpdateTime = null;

function parsePacket(text) {
  text = text.replace(/\n/g, ",").replace(",=Vy", ",Vy");
  ["r2=", "D=", "P=", "M="].forEach(function(k) {
    text = text.split(k).join("," + k);
  });
  const values = {};
  text.split(",").forEach(function(part) {
    part = part.trim();
    if (part.indexOf("=") !== -1) {
      const idx = part.indexOf("=");
      const k = part.slice(0, idx);
      const v = part.slice(idx + 1);
      if (k) values[k] = v;
    }
  });
  return values;
}

function tankStatus(low, high) {
  low = Number(low); high = Number(high);
  if (low === 1 && high === 1) return {text: "FULL", color: "var(--green)"};
  if (low === 1 && high === 0) return {text: "OK", color: "var(--blue)"};
  if (low === 0 && high === 0) return {text: "EMPTY", color: "var(--amber)"};
  return {text: "CHECK SENSOR", color: "var(--red)"};
}

async function refresh() {
  try {
    const res = await fetch("/data", {cache: "no-store"});
    const text = await res.text();
    if (!text.trim()) return;
    const v = parsePacket(text);
    lastValues = v;
    lastUpdateTime = Date.now();

    document.getElementById("v-ry").innerHTML = (v.Vr || "--") + "<span class='unit'>V</span>";
    document.getElementById("v-yb").innerHTML = (v.Vy || "--") + "<span class='unit'>V</span>";
    document.getElementById("v-br").innerHTML = (v.Vb || "--") + "<span class='unit'>V</span>";

    document.getElementById("i-r").innerHTML = (v.Ir || "--") + "<span class='unit'>A</span>";
    document.getElementById("i-y").innerHTML = (v.Iy || "--") + "<span class='unit'>A</span>";
    document.getElementById("i-b").innerHTML = (v.Ib || "--") + "<span class='unit'>A</span>";

    document.getElementById("th-p1").innerHTML = (v.r1 || "--") + "<span class='unit'>A</span>";
    document.getElementById("th-p2").innerHTML = (v.r2 || "--") + "<span class='unit'>A</span>";
    document.getElementById("th-dry").innerHTML = (v.D || "--") + "<span class='unit'>%</span>";

    document.getElementById("t-on").innerHTML = (v.ton || "--") + "<span class='unit'>min</span>";
    document.getElementById("t-off").innerHTML = (v.tof || "--") + "<span class='unit'>min</span>";

    const activePump = v.P === "1" ? "PUMP 2" : "PUMP 1";
    document.getElementById("sys-pump").textContent = activePump;
    document.getElementById("sys-pump-raw").textContent = "(raw=" + (v.P || "--") + ")";

    const mode = v.M === "102" ? "AUTO" : "MANUAL";
    document.getElementById("sys-mode").textContent = mode;
    document.getElementById("sys-mode-raw").textContent = "(raw=" + (v.M || "--") + ")";

    const state = v.PV === "1" ? "RUNNING" : "STOPPED";
    document.getElementById("sys-state").textContent = state;
    document.getElementById("sys-state-raw").textContent = "(raw=" + (v.PV || "--") + ")";

    const bottom = tankStatus(v.L0, v.L1);
    document.getElementById("tank-bottom").textContent = bottom.text;
    document.getElementById("tank-bottom").style.color = bottom.color;
    document.getElementById("tank-bottom-raw").textContent = "(low=" + (v.L0 || "-") + ", high=" + (v.L1 || "-") + ")";

    const top = tankStatus(v.L2, v.L3);
    document.getElementById("tank-top").textContent = top.text;
    document.getElementById("tank-top").style.color = top.color;
    document.getElementById("tank-top-raw").textContent = "(low=" + (v.L2 || "-") + ", high=" + (v.L3 || "-") + ")";
  } catch (e) {
    console.error("Failed to refresh:", e);
  }
}

function updateAgo() {
  if (!lastUpdateTime) { document.getElementById("ago").textContent = "--"; return; }
  const secs = Math.round((Date.now() - lastUpdateTime) / 1000);
  document.getElementById("ago").textContent = secs + "s ago";
}

function generateReport() {
  if (!lastValues) { alert("No data yet."); return; }
  const lines = Object.entries(lastValues).map(function(pair) { return pair[0] + ": " + pair[1]; });
  const blob = new Blob([lines.join("\n")], {type: "text/plain"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "pump_report_" + new Date().toISOString().slice(0,19).replace(/[:T]/g,"-") + ".txt";
  a.click();
  URL.revokeObjectURL(url);
}

refresh();
setInterval(refresh, 3000);
setInterval(updateAgo, 1000);
</script>
</body>
</html>
"""


@app.route("/dashboard")
def dashboard():
    return Response(DASHBOARD_HTML, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
