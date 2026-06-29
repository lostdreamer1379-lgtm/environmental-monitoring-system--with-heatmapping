import serial, time, joblib, pandas as pd, os, collections
import folium, threading, requests, random
from flask import Flask, render_template_string

# ------------------ SERIAL ------------------
ser = serial.Serial('COM9', 9600, timeout=1)
time.sleep(2)

# ------------------ MODEL ------------------
MODEL_PATH = "env_ai_model2.pkl"
model = joblib.load(MODEL_PATH)
last_model_time = os.path.getmtime(MODEL_PATH)

# ------------------ MEMORY -----------------
pred_history = collections.deque(maxlen=10)
aqi_list = []
alerts = []
markers = []

prev_aqi = 0
current_ai = "Waiting..."
current_conf = 0

# SENSOR VALUES
current_temp = 0
current_hum = 0
current_pressure = 0
current_mq2 = 0
current_mq135 = 0
current_gases = ["Normal"]

# ------------------ LOCATION -----------------
try:
    loc = requests.get("http://ip-api.com/json").json()
    base_lat, base_lon = loc["lat"], loc["lon"]
except:
    base_lat, base_lon = 22.57, 88.36

# ------------------ FLASK -------------------
app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>AI Dashboard</title>
<style>
body { margin:0; font-family: 'Segoe UI'; background: linear-gradient(135deg,#0f2027,#203a43,#2c5364); color:white; }
.header { position: sticky; top: 0; z-index: 999; background: rgba(0,0,0,0.7); padding: 10px; }
.container { display:flex; justify-content:space-around; flex-wrap:wrap; }
.card { background: rgba(255,255,255,0.1); border-radius:15px; padding:15px; margin:10px; width:40%; }
.stat { margin:5px 0; }
.alert { background: rgba(255,0,0,0.2); padding:8px; border-radius:8px; margin:5px 0; }
.map-container { margin-top:10px; height:75vh; }
</style>
</head>
<body>

<div class="header">
<h2 style="text-align:center;">🌍 Smart AI Dashboard</h2>

<div class="container">

<div class="card">
<h3>📊 Live Stats</h3>
<p class="stat">🌡 Temp: {{temp}} °C</p>
<p class="stat">💧 Humidity: {{hum}} %</p>
<p class="stat">🌬 Pressure: {{pressure}} hPa</p>
<hr>
<p class="stat">🧪 MQ2: {{mq2}}</p>
<p class="stat">🏭 MQ135: {{mq135}}</p>
<p class="stat">🔍 Gases Detected: {{gases}}</p>
<hr>
<p class="stat">🌫 AQI: {{aqi}}</p>
<p class="stat">🧠 AI: {{ai}}</p>
<p class="stat">Confidence: {{conf}}%</p>
</div>

<div class="card">
<h3>🚨 Alerts</h3>
{% for a in alerts %}
<div class="alert">{{a}}</div>
{% endfor %}
</div>

</div>
</div>

<div class="map-container">
{{map|safe}}
</div>

</body>
</html>
"""

@app.route('/')
def index():
    m = folium.Map(location=[base_lat, base_lon], zoom_start=12)

    # Map markers with full info in popup
    for lat, lon, label, aqi, gases, t, h, p in markers[-50:]:
        color = "green" if aqi < 100 else "orange" if aqi < 200 else "red"
        popup_text = f"""
        <b>AI:</b> {label}<br>
        <b>AQI:</b> {aqi}<br>
        <b>Gases:</b> {', '.join(gases)}<br>
        <b>Temp:</b> {t}°C<br>
        <b>Humidity:</b> {h}%<br>
        <b>Pressure:</b> {p} hPa
        """
        folium.Marker([lat, lon], popup=popup_text, icon=folium.Icon(color=color)).add_to(m)

    return render_template_string(
        HTML,
        map=m._repr_html_(),
        temp=current_temp,
        hum=current_hum,
        pressure=current_pressure,
        mq2=current_mq2,
        mq135=current_mq135,
        gases=", ".join(current_gases),
        aqi=aqi_list[-1] if aqi_list else 0,
        ai=current_ai,
        conf=current_conf,
        alerts=alerts[-5:]
    )

threading.Thread(target=lambda: app.run(debug=False, use_reloader=False), daemon=True).start()

# ------------------ MODEL RELOAD -----------------
def reload_model():
    global model, last_model_time
    t = os.path.getmtime(MODEL_PATH)
    if t != last_model_time:
        model = joblib.load(MODEL_PATH)
        last_model_time = t
        print("🔄 Model Reloaded")

# ------------------ GAS DETECTION -----------------
def detect_gases(mq2, mq135):
    gases = []
    if mq2 > 400:
        gases.append("Smoke/LPG")
    elif mq2 > 250:
        gases.append("Gas Detected")
    if mq135 > 400:
        gases.append("Air Pollution / CO2")
    elif mq135 > 300:
        gases.append("Moderate Pollution")
    return gases if gases else ["Normal"]

# ------------------ MAIN LOOP -----------------
while True:
    try:
        reload_model()
        line = ser.readline().decode(errors='ignore').strip()
        v = line.split(',')
        if len(v) == 5:
            try:
                t, h, p, mq2, mq135 = map(float, v)
            except:
                continue

            # Update sensor values
            current_temp = round(t, 1)
            current_hum = round(h, 1)
            current_pressure = round(p, 1)
            current_mq2 = int(mq2)
            current_mq135 = int(mq135)
            current_gases = detect_gases(mq2, mq135)

            # AQI
            aqi = int((mq135 / 1023) * 500)
            gas_ratio = mq2 / (mq135 + 1.0)

            # ML prediction
            features = pd.DataFrame([[t, h, p, mq2, mq135, aqi, gas_ratio]],
                                    columns=['temp','hum','pressure','mq2','mq135','aqi','gas_ratio'])
            probs = model.predict_proba(features)[0]
            pred = model.classes_[probs.argmax()]
            confidence = round(max(probs)*100, 2)

            pred_history.append(pred)
            final_pred = max(set(pred_history), key=pred_history.count)

            current_ai = final_pred
            current_conf = confidence

            ser.write((final_pred + "\n").encode())

            # AQI history
            aqi_list.append(aqi)
            aqi_list[:] = aqi_list[-100:]

            # Alerts
            if aqi > 300 and (not alerts or alerts[-1] != "🚨 Dangerous AQI!"):
                alerts.append("🚨 Dangerous AQI!")

            # Accurate location around laptop (10–20m)
            lat_offset = random.uniform(-0.00015, 0.00015)
            lon_offset = random.uniform(-0.00015, 0.00015)
            lat = base_lat + lat_offset
            lon = base_lon + lon_offset

            markers.append((lat, lon, final_pred, aqi, current_gases, current_temp, current_hum, current_pressure))

            print(f"AQI:{aqi} AI:{final_pred} ({confidence}%) | Gases: {current_gases}")

    except Exception as e:
        print("Error:", e)