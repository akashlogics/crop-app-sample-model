"""
Flask API server for the Intelligent Crop Recommendation System.
Updated to handle new frontend fields: soil_type, irrig_type, land_size.
Weather endpoint now also returns wind_speed and pressure.
New endpoints: /select-crop, /water-schedule
"""

import os
import json
import datetime
import requests
import joblib
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from database import init_db, save_recommendation, get_history, update_selected_crop

load_dotenv()

app = Flask(__name__)
CORS(app)

# ── Load ML model ──────────────────────────────────────────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
rf_model      = joblib.load(os.path.join(MODEL_DIR, "rf_model.pkl"))
label_encoder = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

# Crop information dictionary — emoji, description, fertilizer
CROP_INFO = {
    "rice":        {"emoji": "🌾", "desc": "Paddy crop, needs high water.",        "fert": "Urea + DAP"},
    "maize":       {"emoji": "🌽", "desc": "Cereal grain, versatile use.",          "fert": "NPK 20-20-20"},
    "chickpea":    {"emoji": "🫘", "desc": "Legume, fixes nitrogen.",               "fert": "SSP + MOP"},
    "kidneybeans": {"emoji": "🫘", "desc": "Protein-rich pulse.",                   "fert": "DAP + Potash"},
    "pigeonpeas":  {"emoji": "🌿", "desc": "Drought-tolerant pulse.",               "fert": "Phosphorus-rich"},
    "mothbeans":   {"emoji": "🌱", "desc": "Drought resistant legume.",             "fert": "Low nitrogen"},
    "mungbean":    {"emoji": "🫘", "desc": "Short-duration pulse.",                 "fert": "DAP"},
    "blackgram":   {"emoji": "🫘", "desc": "High protein pulse.",                   "fert": "NPK blend"},
    "lentil":      {"emoji": "🫘", "desc": "Cool-season legume.",                   "fert": "SSP"},
    "pomegranate": {"emoji": "🍎", "desc": "Fruit crop, drought tolerant.",         "fert": "MOP + Urea"},
    "banana":      {"emoji": "🍌", "desc": "Tropical fruit, high yield.",           "fert": "NPK 10-10-10"},
    "mango":       {"emoji": "🥭", "desc": "Tropical fruit tree.",                  "fert": "NPK 12-12-12"},
    "grapes":      {"emoji": "🍇", "desc": "Vineyard crop.",                        "fert": "Potassium-rich"},
    "watermelon":  {"emoji": "🍉", "desc": "Summer fruit, high water.",             "fert": "Calcium + Boron"},
    "muskmelon":   {"emoji": "🍈", "desc": "Sweet summer fruit.",                   "fert": "NPK 13-0-46"},
    "apple":       {"emoji": "🍏", "desc": "Temperate fruit tree.",                 "fert": "Calcium Nitrate"},
    "orange":      {"emoji": "🍊", "desc": "Citrus fruit.",                         "fert": "Citrus NPK blend"},
    "papaya":      {"emoji": "🍈", "desc": "Tropical fruit, fast growing.",         "fert": "Urea + MOP"},
    "coconut":     {"emoji": "🥥", "desc": "Coastal crop, tall palm.",              "fert": "NPK + Mg"},
    "cotton":      {"emoji": "🌿", "desc": "Cash crop, fiber plant.",               "fert": "Urea + DAP"},
    "jute":        {"emoji": "🌾", "desc": "Natural fiber crop.",                   "fert": "Nitrogen-heavy"},
    "coffee":      {"emoji": "☕", "desc": "Plantation crop.",                       "fert": "NPK 17-17-17"},
}

# Daily water requirement per plant (litres) under normal conditions.
# Values are reduced by rainfall already present on that day.
CROP_WATER_BASE = {
    "rice":        8.0,
    "maize":       4.5,
    "chickpea":    2.5,
    "kidneybeans": 3.0,
    "pigeonpeas":  2.0,
    "mothbeans":   1.8,
    "mungbean":    2.5,
    "blackgram":   2.5,
    "lentil":      2.0,
    "pomegranate": 3.5,
    "banana":      10.0,
    "mango":       5.0,
    "grapes":      4.0,
    "watermelon":  6.0,
    "muskmelon":   5.0,
    "apple":       4.5,
    "orange":      5.0,
    "papaya":      6.0,
    "coconut":     8.0,
    "cotton":      4.0,
    "jute":        5.5,
    "coffee":      3.5,
}


# ── /recommend ─────────────────────────────────────────────────────────────────
@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()

    # Core fields required by the ML model
    required = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    try:
        N           = float(data["N"])
        P           = float(data["P"])
        K           = float(data["K"])
        temperature = float(data["temperature"])
        humidity    = float(data["humidity"])
        ph          = float(data["ph"])
        rainfall    = float(data["rainfall"])

        # Optional new fields from frontend
        location   = data.get("location",   "Unknown")
        soil_type  = data.get("soil_type",  "Unknown")
        irrig_type = data.get("irrig_type", "Unknown")
        land_size  = data.get("land_size")  # may be None

        features = np.array([[N, P, K, temperature, humidity, ph, rainfall]])

        proba   = rf_model.predict_proba(features)[0]
        classes = label_encoder.classes_

        # Top 5 crops sorted by confidence
        top_indices = np.argsort(proba)[::-1][:5]
        results = []
        for idx in top_indices:
            crop = classes[idx]
            conf = round(float(proba[idx]) * 100, 2)
            info = CROP_INFO.get(crop, {"emoji": "🌱", "desc": "", "fert": "General NPK"})
            results.append({
                "crop":        crop,
                "confidence":  conf,
                "emoji":       info["emoji"],
                "description": info["desc"],
                "fertilizer":  info["fert"],
            })

        top = results[0]

        # Save to DB (includes new soil_type + irrigation fields)
        history_id = save_recommendation({
            "location":    location,
            "soil_type":   soil_type,
            "irrigation":  irrig_type,
            "land_size":   land_size,
            "N":           N, "P": P, "K": K,
            "temperature": temperature,
            "humidity":    humidity,
            "ph":          ph,
            "rainfall":    rainfall,
            "top_crop":    top["crop"],
            "confidence":  top["confidence"],
            "all_results": json.dumps(results),
        })

        # Generate weather advisory based on current conditions
        advisory = get_advisory(temperature, humidity, rainfall)

        # Add soil-specific tip if soil type is provided
        if soil_type and soil_type != "Unknown":
            advisory.extend(get_soil_advisory(soil_type))

        return jsonify({
            "history_id":          history_id,
            "top_recommendation":  top,
            "all_recommendations": results,
            "advisory":            advisory,
            "input_summary": {
                "location":  location,
                "soil_type": soil_type,
                "irrigation": irrig_type,
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /select-crop ───────────────────────────────────────────────────────────────
@app.route("/select-crop", methods=["POST"])
def select_crop():
    """
    Save the farmer's chosen crop against their recommendation record.
    Body: { "history_id": <int>, "selected_crop": "<crop_name>" }
    """
    data = request.get_json()
    history_id    = data.get("history_id")
    selected_crop = data.get("selected_crop", "").strip().lower()

    if not history_id or not selected_crop:
        return jsonify({"error": "history_id and selected_crop are required"}), 400

    try:
        update_selected_crop(int(history_id), selected_crop)
        info = CROP_INFO.get(selected_crop, {"emoji": "🌱", "desc": "", "fert": "General NPK"})
        return jsonify({
            "ok":           True,
            "selected_crop": selected_crop,
            "emoji":         info["emoji"],
            "message":       f"✅ {selected_crop.title()} saved as your planting choice!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /water-schedule ────────────────────────────────────────────────────────────
@app.route("/water-schedule", methods=["GET"])
def water_schedule():
    """
    Return a 4-day watering schedule for a chosen crop, adjusted for forecast rain.
    Query params: city=<str>, crop=<str>
    """
    city = request.args.get("city", "Delhi")
    crop = request.args.get("crop", "").strip().lower()

    if not crop:
        return jsonify({"error": "crop parameter is required"}), 400

    base_litres = CROP_WATER_BASE.get(crop, 4.0)

    # Generate 4 consecutive dates starting tomorrow
    today = datetime.date.today()
    schedule = []

    # Try to get real forecast data
    forecast_data = []
    if WEATHER_API_KEY:
        try:
            url = (
                f"https://api.openweathermap.org/data/2.5/forecast"
                f"?q={city}&appid={WEATHER_API_KEY}&units=metric&cnt=32"
            )
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            raw = r.json()

            from collections import defaultdict
            day_buckets = defaultdict(list)
            for item in raw["list"]:
                dt = datetime.datetime.utcfromtimestamp(item["dt"])
                day_key = dt.date()
                day_buckets[day_key].append(item)

            for day_date, entries in sorted(day_buckets.items()):
                if day_date <= today:
                    continue
                rains  = [e.get("rain", {}).get("3h", 0) for e in entries]
                humids = [e["main"]["humidity"] for e in entries]
                cond   = entries[len(entries) // 2]["weather"][0]
                forecast_data.append({
                    "date":     day_date,
                    "rainfall": round(sum(rains), 1),
                    "humidity": round(sum(humids) / len(humids)),
                    "icon":     get_weather_icon(cond["main"]),
                    "desc":     cond["description"].title(),
                })
                if len(forecast_data) == 4:
                    break
        except Exception:
            pass  # Fall through to mock data

    # Fill missing days with mock data
    while len(forecast_data) < 4:
        offset = len(forecast_data) + 1
        d = today + datetime.timedelta(days=offset)
        forecast_data.append({
            "date":     d,
            "rainfall": round(2.0 * (offset % 3), 1),
            "humidity": 65,
            "icon":     ["☀️", "⛅", "🌧️", "⛅"][offset % 4 - 1],
            "desc":     ["Sunny", "Partly Cloudy", "Light Rain", "Mostly Cloudy"][offset % 4 - 1],
        })

    # Build the irrigation schedule for each of the 4 days
    for i, day in enumerate(forecast_data[:4]):
        date_obj = day["date"]
        rain_mm  = day["rainfall"]

        # Each mm of rainfall roughly provides 1 litre per m² — scale to plant level
        rain_offset = min(rain_mm * 0.3, base_litres * 0.8)  # cap relief at 80%
        recommended = round(max(base_litres - rain_offset, 0.5), 1)

        if rain_mm > 10:
            note = "🌧️ Heavy rain expected — skip irrigation today."
            recommended = 0.0
        elif rain_mm > 4:
            note = "🌦️ Light rain — reduced watering needed."
        elif day["humidity"] > 85:
            note = "💧 High humidity — reduce watering slightly."
            recommended = round(recommended * 0.85, 1)
        else:
            note = "☀️ Normal conditions — follow the schedule."

        schedule.append({
            "day_num":           i + 1,
            "date":              date_obj.strftime("%d %b %Y"),
            "weekday":           date_obj.strftime("%A"),
            "icon":              day["icon"],
            "weather_desc":      day["desc"],
            "rainfall_mm":       rain_mm,
            "humidity_pct":      day["humidity"],
            "recommended_water_L": recommended,
            "note":              note,
        })

    crop_info = CROP_INFO.get(crop, {"emoji": "🌱", "desc": "", "fert": ""})

    return jsonify({
        "crop":          crop,
        "emoji":         crop_info["emoji"],
        "base_litres":   base_litres,
        "city":          city,
        "schedule":      schedule,
        "next_call_note": "📅 This schedule covers the next 4 days. Return after Day 4 to get an updated irrigation plan.",
    })


def get_advisory(temp, humidity, rainfall):
    """Generate weather-based farming advisories."""
    tips = []
    if temp > 35:
        tips.append("⚠️ High temperature — ensure adequate irrigation and mulching.")
    elif temp < 15:
        tips.append("❄️ Low temperature — consider frost-tolerant varieties.")

    if humidity > 85:
        tips.append("💧 High humidity — watch for fungal diseases; improve ventilation.")
    elif humidity < 40:
        tips.append("🌵 Low humidity — consider cover crops or mulching to retain moisture.")

    if rainfall < 50:
        tips.append("🏜️ Low rainfall — supplemental irrigation strongly recommended.")
    elif rainfall > 250:
        tips.append("🌧️ Heavy rainfall expected — ensure proper field drainage.")

    if not tips:
        tips.append("✅ Weather conditions are optimal for farming.")
    return tips


def get_soil_advisory(soil_type):
    """Generate soil-type-specific farming tips."""
    advisories = {
        "Alluvial Soil":  ["🌱 Alluvial soil is highly fertile — excellent for most crops."],
        "Black Soil":     ["🌿 Black soil retains moisture well — ideal for cotton and soybean."],
        "Red Soil":       ["🧪 Red soil is low in nutrients — apply NPK fertilizers before sowing."],
        "Laterite Soil":  ["⚗️ Laterite soil is acidic — apply lime to adjust pH before planting."],
        "Sandy Soil":     ["💦 Sandy soil drains fast — frequent irrigation and organic matter needed."],
        "Loamy Soil":     ["✨ Loamy soil has great structure — minimal amendments needed."],
        "Clay Soil":      ["🏗️ Clay soil retains water — ensure proper drainage to avoid waterlogging."],
    }
    return advisories.get(soil_type, [])


# ── /weather ───────────────────────────────────────────────────────────────────
@app.route("/weather", methods=["GET"])
def weather():
    city = request.args.get("city", "Delhi")

    if not WEATHER_API_KEY:
        # Return mock data when no API key is configured
        return jsonify({
            "city":        city,
            "temperature": 28.5,
            "humidity":    72,
            "rainfall":    3.2,
            "wind_speed":  14,
            "pressure":    1013,
            "description": "Partly Cloudy (Demo)",
            "icon":        "⛅",
            "source":      "mock",
            "advisory":    get_advisory(28.5, 72, 3.2)
        })

    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        d = r.json()

        temp_val  = round(d["main"]["temp"], 1)
        humid_val = d["main"]["humidity"]
        rain_val  = round(d.get("rain", {}).get("1h", 0), 2)
        return jsonify({
            "city":        d.get("name", city),
            "temperature": temp_val,
            "humidity":    humid_val,
            "rainfall":    rain_val,
            "wind_speed":  round(d.get("wind", {}).get("speed", 0) * 3.6, 1),
            "pressure":    d["main"].get("pressure", 1013),
            "description": d["weather"][0]["description"].title(),
            "icon":        get_weather_icon(d["weather"][0]["main"]),
            "source":      "live",
            "advisory":    get_advisory(temp_val, humid_val, rain_val)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_weather_icon(condition):
    icons = {
        "Clear": "☀️", "Clouds": "⛅", "Rain": "🌧️",
        "Drizzle": "🌦️", "Thunderstorm": "⛈️",
        "Snow": "❄️", "Mist": "🌫️", "Fog": "🌁", "Haze": "🌫️"
    }
    return icons.get(condition, "🌡️")


# ── /forecast ──────────────────────────────────────────────────────────────────
@app.route("/forecast", methods=["GET"])
def forecast():
    city = request.args.get("city", "Delhi")

    if not WEATHER_API_KEY:
        # Mock 4-day forecast when no API key
        days  = ["Mon", "Tue", "Wed", "Thu"]
        icons = ["☀️", "⛅", "🌧️", "⛅"]
        return jsonify([
            {
                "day":         days[i],
                "icon":        icons[i],
                "temp_min":    round(24 - i, 1),
                "temp_max":    round(32 - i, 1),
                "humidity":    65 + i * 3,
                "rainfall":    round(i * 1.5, 1),
                "description": ["Sunny", "Partly Cloudy", "Light Rain", "Mostly Cloudy"][i],
            }
            for i in range(4)
        ])

    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?q={city}&appid={WEATHER_API_KEY}&units=metric&cnt=32"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        from collections import defaultdict
        day_buckets = defaultdict(list)
        for item in data["list"]:
            dt = datetime.datetime.utcfromtimestamp(item["dt"])
            day_key = dt.strftime("%a")
            day_buckets[day_key].append(item)

        result = []
        for day_name, entries in list(day_buckets.items())[:4]:
            temps  = [e["main"]["temp"] for e in entries]
            humids = [e["main"]["humidity"] for e in entries]
            rains  = [e.get("rain", {}).get("3h", 0) for e in entries]
            cond   = entries[len(entries) // 2]["weather"][0]
            result.append({
                "day":         day_name,
                "icon":        get_weather_icon(cond["main"]),
                "temp_min":    round(min(temps), 1),
                "temp_max":    round(max(temps), 1),
                "humidity":    round(sum(humids) / len(humids)),
                "rainfall":    round(sum(rains), 1),
                "description": cond["description"].title(),
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /history ───────────────────────────────────────────────────────────────────
@app.route("/history", methods=["GET"])
def history():
    rows = get_history(limit=20)
    return jsonify(rows)


# ── /feature-importance ────────────────────────────────────────────────────────
@app.route("/feature-importance", methods=["GET"])
def feature_importance():
    FEATURES = ["N", "P", "K", "Temperature", "Humidity", "pH", "Rainfall"]
    result = [
        {"feature": f, "importance": round(float(i) * 100, 2)}
        for f, i in zip(FEATURES, rf_model.feature_importances_)
    ]
    result.sort(key=lambda x: -x["importance"])
    return jsonify(result)


# ── /health ────────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": "Random Forest", "crops": len(label_encoder.classes_)})


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("🌱 CropAI API running → http://localhost:5000")
    print("📋 Endpoints: /recommend  /select-crop  /water-schedule  /weather  /forecast  /history  /feature-importance  /health")
    app.run(debug=True, port=5000, use_reloader=False)
