"""
Train and save the Random Forest crop recommendation model.
Run this once to generate the model file.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

# ── Load dataset ─────────────────────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/crop_data.csv")
df = pd.read_csv(DATA_PATH)

print(f"Dataset shape: {df.shape}")
print(f"Crops: {df['label'].unique()}")

# ── Features & target ────────────────────────────────────────────────────────
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
X = df[FEATURES]
y = df["label"]

# Encode labels
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# ── Train / test split ───────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42
)

# ── Random Forest Classifier ──────────────────────────────────────────────────
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred = rf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"\n✅ Model Accuracy: {acc * 100:.2f}%")
print("\nClassification Report:")
present = sorted(set(y_test))
print(classification_report(y_test, y_pred, labels=present, target_names=le.classes_[present]))

# Feature importance
print("\nFeature Importances:")
for feat, imp in sorted(
    zip(FEATURES, rf.feature_importances_), key=lambda x: -x[1]
):
    print(f"  {feat}: {imp:.4f}")

# ── Save model & encoder ──────────────────────────────────────────────────────
MODEL_DIR = os.path.dirname(__file__)
joblib.dump(rf, os.path.join(MODEL_DIR, "rf_model.pkl"))
joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.pkl"))

print("\n✅ Model saved: backend/model/rf_model.pkl")
print("✅ Encoder saved: backend/model/label_encoder.pkl")
