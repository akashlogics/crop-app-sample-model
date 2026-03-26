"""
SQLite database setup for storing crop recommendations.
Updated to include soil_type, irrigation_type and selected_crop columns.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "recommendations.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
            location      TEXT,
            soil_type     TEXT,
            irrigation    TEXT,
            land_size     REAL,
            nitrogen      REAL,
            phosphorus    REAL,
            potassium     REAL,
            temperature   REAL,
            humidity      REAL,
            ph            REAL,
            rainfall      REAL,
            top_crop      TEXT,
            confidence    REAL,
            all_results   TEXT,
            selected_crop TEXT
        )
    """)

    # Migrate existing DB: add new columns if they don't exist yet
    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(recommendations)")]
    migrations = [
        ("soil_type",     "TEXT"),
        ("irrigation",    "TEXT"),
        ("land_size",     "REAL"),
        ("selected_crop", "TEXT"),
    ]
    for col, col_type in migrations:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE recommendations ADD COLUMN {col} {col_type}")
            print(f"  ✅ Added column: {col}")

    conn.commit()
    conn.close()
    print("✅ Database initialized / migrated.")


def save_recommendation(data: dict) -> int:
    """Insert a new recommendation row and return its id."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recommendations
            (location, soil_type, irrigation, land_size,
             nitrogen, phosphorus, potassium,
             temperature, humidity, ph, rainfall,
             top_crop, confidence, all_results)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("location",   "Unknown"),
        data.get("soil_type",  "Unknown"),
        data.get("irrigation", "Unknown"),
        data.get("land_size"),
        data["N"], data["P"], data["K"],
        data["temperature"], data["humidity"],
        data["ph"], data["rainfall"],
        data["top_crop"], data["confidence"],
        data["all_results"]
    ))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def update_selected_crop(history_id: int, crop: str):
    """Store the farmer's chosen crop against a recommendation record."""
    conn = get_db()
    conn.execute(
        "UPDATE recommendations SET selected_crop = ? WHERE id = ?",
        (crop, history_id)
    )
    conn.commit()
    conn.close()


def get_history(limit=20):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM recommendations
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()
