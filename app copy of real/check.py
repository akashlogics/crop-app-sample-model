import pandas as pd

# Load dataset
df = pd.read_csv("crop_recommendation_dataset.csv")

# Get unique values from a column
unique_values = df['label'].unique()

print(unique_values)