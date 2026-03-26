import pandas as pd
import numpy as np

# Set seed for reproducibility
np.random.seed(42)

def generate_crop_dataset(num_rows=500):
    # Define crop profiles based on weather conditions
    # Format: 'CropName': [Temp_Range, Humidity_Range, Rainfall_Range]
    crop_profiles = {
        'Rice': [(20, 32), (70, 90), (150, 300)],
        'Maize': [(18, 30), (50, 80), (60, 120)],
        'Cotton': [(24, 35), (40, 60), (50, 100)],
        'Sugarcane': [(22, 38), (45, 75), (100, 250)],
        'Millets': [(25, 40), (30, 50), (30, 70)],
        'Pulses': [(20, 32), (40, 60), (40, 80)],
        'Groundnuts': [(23, 33), (50, 70), (50, 125)]
    }

    data = []
    crops = list(crop_profiles.keys())
    
    for _ in range(num_rows):
        # Pick a random crop to generate a data point for
        crop = np.random.choice(crops)
        t_range, h_range, r_range = crop_profiles[crop]
        
        # Add some random "noise" to make the ML model learn better
        temp = round(np.random.uniform(t_range[0], t_range[1]), 2)
        hum = round(np.random.uniform(h_range[0], h_range[1]), 2)
        rain = round(np.random.uniform(r_range[0], r_range[1]), 2)
        
        data.append([temp, hum, rain, crop])

    # Create DataFrame
    df = pd.DataFrame(data, columns=['temperature', 'humidity', 'rainfall', 'label'])
    
    # Save to CSV
    df.to_csv('crop_recommendation_dataset.csv', index=False)
    print(f"Successfully generated {num_rows} rows in 'crop_recommendation_dataset.csv'")
    return df

# Generate the data
df = generate_crop_dataset(500)

# Display first few rows to verify
print(df.head())