import os
import time
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, jsonify, request, render_template_string, abort

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "")
lock = Lock()

state = {
    "temperature_c": None,
    "humidity_percent": None,
    "pump_on": False,
    "pump_requested": False,
    "panel_position": "UNKNOWN",
    "device_id": "AGRIVOLTAIC_01",
    "last_seen": None,
    "history": [],
}

def authorized():
    # Set API_KEY in Render's Environment settings. Never hardcode it in GitHub.
    supplied = request.headers.get("X-API-Key", "")
    return bool(API_KEY) and supplied == API_KEY

@app.get("/")
def dashboard():
    return render_template_string(PAGE)

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

@app.post("/api/telemetry")
def telemetry():
    if not authorized():
        abort(401)
    payload = request.get_json(silent=True) or {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        temperature = float(payload["temperature_c"])
        humidity = float(payload["humidity_percent"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "temperature_c and humidity_percent are required numbers"}), 400

    with lock:
        state["temperature_c"] = temperature
        state["humidity_percent"] = humidity
        state["pump_on"] = bool(payload.get("pump_on", False))
        state["panel_position"] = str(payload.get("panel_position", "UNKNOWN"))
        state["device_id"] = str(payload.get("device_id", "AGRIVOLTAIC_01"))
        state["last_seen"] = now
        state["history"].append({
            "time": now,
            "temperature_c": temperature,
            "humidity_percent": humidity,
            "pump_on": state["pump_on"],
            "panel_position": state["panel_position"],
        })
        state["history"] = state["history"][-60:]

    return jsonify({"ok": True, "received_at": now})

@app.get("/api/state")
def get_state():
    if not authorized():
        abort(401)
    with lock:
        return jsonify({
            "temperature_c": state["temperature_c"],
            "humidity_percent": state["humidity_percent"],
            "pump_on": state["pump_on"],
            "pump_requested": state["pump_requested"],
            "panel_position": state["panel_position"],
            "device_id": state["device_id"],
            "last_seen": state["last_seen"],
            "history": state["history"],
        })

@app.post("/api/pump")
def set_pump():
    if not authorized():
        abort(401)
    payload = request.get_json(silent=True) or {}
    if "on" not in payload or not isinstance(payload["on"], bool):
        return jsonify({"error": "Send JSON with boolean field 'on'"}), 400
    with lock:
        state["pump_requested"] = payload["on"]
    return jsonify({"ok": True, "pump_requested": state["pump_requested"]})

PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agrivoltaic Monitor</title>
<style>
:root{font-family:system-ui,Arial,sans-serif;color:#182230;background:#f3f6f8}
body{max-width:960px;margin:0 auto;padding:22px}
header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
h1{margin-bottom:4px} .muted{color:#64748b;font-size:.92rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:20px 0}
.card{background:white;border:1px solid #dce3e8;border-radius:14px;padding:18px;box-shadow:0 2px 7px #1020300a}
.value{font-size:2rem;font-weight:700;margin:8px 0}
button{border:0;border-radius:9px;padding:12px 18px;font-weight:650;cursor:pointer;margin:4px}
.on{background:#16794b;color:white}.off{background:#b42318;color:white}
input{padding:10px;border:1px solid #bac5d1;border-radius:8px;width:min(100%,330px)}
table{border-collapse:collapse;width:100%;background:white}td,th{padding:9px;border-bottom:1px solid #e4e9ee;text-align:left}
small{color:#64748b}.status{font-weight:600}
</style>
</head>
<body>
<header>
  <div><h1>Agrivoltaic Monitor</h1><div class="muted">Irish potato prototype · ESP32 + DHT11 · Render</div></div>
  <div id="connection" class="status">Waiting for device…</div>
</header>

<div class="card">
  <label for="token"><b>Device control key</b></label><br>
  <input id="token" type="password" placeholder="Enter the API_KEY configured in Render" autocomplete="off">
  <button onclick="saveToken()">Use key</button>
  <p class="muted">For this prototype, enter the shared API key configured in Render. Do not share it publicly.</p>
</div>

<div class="grid">
  <div class="card"><div class="muted">Temperature</div><div class="value" id="temp">—</div><div>°C</div></div>
  <div class="card"><div class="muted">Relative humidity</div><div class="value" id="humidity">—</div><div>%</div></div>
  <div class="card"><div class="muted">Panel position</div><div class="value" id="panel">—</div><div>Temperature-based demo</div></div>
  <div class="card"><div class="muted">Pump state reported by ESP32</div><div class="value" id="pump">—</div><div id="lastseen" class="muted">No telemetry yet</div></div>
</div>

<div class="card">
  <h2>Manual irrigation control</h2>
  <p class="muted">The pump is controlled manually because no soil-moisture sensor is connected. The firmware automatically turns it off after 10 seconds.</p>
  <button class="on" onclick="pumpControl(true)">Turn pump ON</button>
  <button class="off" onclick="pumpControl(false)">Turn pump OFF</button>
  <span id="message" class="muted"></span>
</div>

<div class="card" style="margin-top:14px">
  <h2>Recent readings</h2>
  <p class="muted">Latest readings held in the running app's memory (up to 60 samples). This demo does not provide permanent storage.</p>
  <div style="overflow-x:auto">
  <table><thead><tr><th>Time (UTC)</th><th>Temp °C</th><th>Humidity %</th><th>Pump</th><th>Panel</th></tr></thead>
  <tbody id="history"><tr><td colspan="5">Waiting for telemetry…</td></tr></tbody></table>
  </div>
</div>

<script>
let apiKey = "";
function saveToken(){ apiKey=document.getElementById("token").value.trim(); refresh(); }
async function requestJSON(path, options={}){
  const headers=Object.assign({"Content-Type":"application/json","X-API-Key":apiKey},options.headers||{});
  const response=await fetch(path,Object.assign({},options,{headers}));
  if(!response.ok) throw new Error("HTTP "+response.status);
  return response.json();
}
async function pumpControl(on){
  if(!apiKey){document.getElementById("message").textContent=" Enter the API key first.";return;}
  try{
    await requestJSON("/api/pump",{method:"POST",body:JSON.stringify({on})});
    document.getElementById("message").textContent=on?" Pump ON requested.":" Pump OFF requested.";
  }catch(e){document.getElementById("message").textContent=" Control failed: "+e.message;}
}
async function refresh(){
  if(!apiKey){document.getElementById("connection").textContent="Enter API key to load data";return;}
  try{
    const d=await requestJSON("/api/state");
    document.getElementById("temp").textContent=d.temperature_c==null?"—":Number(d.temperature_c).toFixed(1);
    document.getElementById("humidity").textContent=d.humidity_percent==null?"—":Number(d.humidity_percent).toFixed(1);
    document.getElementById("panel").textContent=d.panel_position||"—";
    document.getElementById("pump").textContent=d.pump_on?"ON":"OFF";
    document.getElementById("lastseen").textContent=d.last_seen?"Last received: "+d.last_seen:"No telemetry yet";
    document.getElementById("connection").textContent=d.last_seen?"API reachable · latest telemetry shown":"API reachable · waiting for ESP32";
    const rows=(d.history||[]).slice().reverse().map(x=>`<tr><td>${x.time}</td><td>${Number(x.temperature_c).toFixed(1)}</td><td>${Number(x.humidity_percent).toFixed(1)}</td><td>${x.pump_on?"ON":"OFF"}</td><td>${x.panel_position}</td></tr>`).join("");
    document.getElementById("history").innerHTML=rows||'<tr><td colspan="5">Waiting for telemetry…</td></tr>';
  }catch(e){document.getElementById("connection").textContent="Waiting for valid key/device"; }
}
setInterval(refresh,4000);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
