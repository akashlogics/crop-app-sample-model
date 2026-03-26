from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import numpy as np
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# 1. Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# 2. Load your ML Model
try:
    with open('crop_model.pkl', 'rb') as f:
        model = pickle.load(f)
except:
    model = None

# Create Database tables
with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(username=request.form['username'], password=hashed_pw)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Registration Successful! Please Login.")
            return redirect(url_for('login'))
        except:
            flash("Username already exists.")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash("Invalid Credentials")
    return render_template('login.html')

def get_live_weather(city_name):
    """Fetches real-time data to pre-fill the dashboard form."""
    api_key = "1f2015128ecaa29750b8dc657ee3b2de"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name},IN&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            return {
                "temp": data['main']['temp'],
                "hum": data['main']['humidity'],
                "rain": data.get('rain', {}).get('1h', 0.0)
            }
    except Exception as e:
        print(f"API Error: {e}")
    
    # Fallback values if API fails
    return {"temp": 0.0, "hum": 0.0, "rain": 0.0}

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 1. Fetch live data for the default city
    weather = get_live_weather("Coimbatore")
    
    # 2. Pass live data to the form template
    return render_template('dashboard.html', 
                           temp=weather['temp'], 
                           hum=weather['hum'], 
                           rain=weather['rain'])

IRRIGATION_MAP = {
    'rice': 'Flood Irrigation',
    'maize': 'Furrow Irrigation',
    'cotton': 'Drip Irrigation',
    'sugarcane': 'Drip Irrigation',
    'millets': 'Sprinkler Irrigation',
    'pulses': 'Sprinkler Irrigation',
    'groundnuts': 'Drip Irrigation'
}

@app.route('/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get data from Dashboard Form
    temp = float(request.form['temp'])
    hum = float(request.form['hum'])
    rain = float(request.form['rain'])
    user_crop = request.form['user_crop'].strip().lower()

    # ML Prediction
    prediction = "rice" # Default fallback
    if model:
        pred_array = np.array([[temp, hum, rain]])
        prediction = model.predict(pred_array)[0].lower()

    # Logic 1: Crop Suitability
    if user_crop == prediction:
        crop_msg = f"Okie! You can start growing {user_crop.capitalize()}."
        crop_status = "success"
    else:
        crop_msg = f"Weather isn't ideal for {user_crop.capitalize()}. Suggesting {prediction.capitalize()}."
        crop_status = "warning"

    # Pass the predicted crop to the result page so we can check irrigation next
    return render_template('result.html', 
                           message=crop_msg, 
                           status=crop_status, 
                           predicted=prediction,
                           user_crop=user_crop)

@app.route('/check_irrigation', methods=['POST'])
def check_irrigation():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    predicted_crop = request.form['predicted_crop'].lower()
    selected_irrigation = request.form['irrigation_type']
    
    # 1. Logic for Irrigation Match
    ideal_irrigation = IRRIGATION_MAP.get(predicted_crop, "Drip Irrigation")
    
    if selected_irrigation == ideal_irrigation:
        # Define irr_msg here so it's not "undefined"
        irr_msg = f"Perfect! You can proceed with {selected_irrigation} for {predicted_crop.capitalize()}."
        status = "success"
    else:
        # Define irr_msg here too
        irr_msg = f"{selected_irrigation} is not ideal for {predicted_crop.capitalize()}. We suggest using {ideal_irrigation} instead."
        status = "warning"

    # 2. Get Weather Context (using your API values)
    # In a full app, you'd pull these from the dashboard form or session
    temp, rain = 32.0, 0.0 
    
    # 3. Calculate Water Quantity
    water_qty = calculate_water_needs(predicted_crop, temp, rain)

    # 4. Now 'irr_msg' is defined and safe to send to the template
    return render_template('irrigation_result.html', 
                           message=irr_msg, 
                           status=status, 
                           water_qty=water_qty,
                           crop=predicted_crop)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

def calculate_water_needs(crop, temp, rain):
    # Base weekly water needs (liters per square meter) for crops
    base_needs = {
        'rice': 35,
        'maize': 25,
        'cotton': 20,
        'sugarcane': 40,
        'millets': 12,
        'pulses': 15,
        'groundnuts': 18
    }
    
    # Get base value or default to 20
    base = base_needs.get(crop.lower(), 20)
    
    # Adjust for high temperature (if > 30°C, increase by 20%)
    if temp > 30:
        base *= 1.2
        
    # Adjust for rainfall (subtract rainfall from the weekly need)
    # OpenWeather rain is usually mm (1mm = 1 liter per m2)
    weekly_predicted_rain = rain * 7 
    final_need = max(0, base - weekly_predicted_rain)
    
    return round(final_need, 1)

if __name__ == '__main__':
    app.run(debug=True)