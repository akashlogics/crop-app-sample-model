import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle

# 1. Load the dataset you generated
df = pd.read_csv('crop_recommendation_dataset.csv')

# 2. Separate Features (X) and Target (y)
X = df[['temperature', 'humidity', 'rainfall']]
y = df['label']

# 3. Split data (80% Training, 20% Testing)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Initialize and Train Random Forest
# n_estimators=100 means we are using 100 decision trees for better accuracy
model = RandomForestClassifier(n_estimators=100, criterion='entropy', random_state=42)
model.fit(X_train, y_train)

# 5. Evaluate Accuracy
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"--- Model Training Complete ---")
print(f"Accuracy Score: {accuracy * 100:.2f}%")
print("\nDetailed Classification Report:")
print(classification_report(y_test, y_pred))

# 6. SAVE THE MODEL (Crucial for your Flask App)
with open('crop_model.pkl', 'wb') as f:
    pickle.dump(model, f)
print("\nModel saved as 'crop_model.pkl'")