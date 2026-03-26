import requests

def get_weather_data(city_name):
    # Your OpenWeatherMap API Key
    api_key = "1f2015128ecaa29750b8dc657ee3b2de"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name},IN&appid={api_key}&units=metric"

    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            # --- 1. CORE DATA FOR ML MODEL ---
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            # Default to 0.0 if 'rain' key is missing in API response
            rain = data.get('rain', {}).get('1h', 0.0)
            
            # --- 2. ADDITIONAL WEATHER DATA ---
            clouds = data.get('clouds', {}).get('all', 0)
            wind = data.get('wind', {}).get('speed', 0)
            desc = data['weather'][0]['description']

            # --- 3. PRINTING DIRECTLY TO CMD ---
            print("-" * 30)
            print(f"CITY: {city_name.upper()}")
            print(f"Condition: {desc.capitalize()}")
            print(f"Temp: {temp}°C")
            print(f"Humidity: {humidity}%")
            print(f"Rain (1h): {rain}mm")
            print(f"Cloudiness: {clouds}%")
            print(f"Wind Speed: {wind} m/s")
            print("-" * 30)

            # Returns list of features for your model.predict()
            return [temp, humidity, rain, clouds, wind]
        
        else:
            print(f"Error: {data.get('message', 'Invalid City')}")
            return None

    except Exception as e:
        print(f"Request failed: {e}")
        return None

# Execute to see results in CMD
weather_features = get_weather_data("Coimbatore")