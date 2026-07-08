import os
from datetime import timedelta


class Config:
    # --- Storage ---
    # Where the JSON data files live. Mount this as a volume in Docker so
    # data survives container restarts.
    DATA_DIR = os.environ.get(
        "DATA_DIR",
        os.path.join(os.path.dirname(__file__), "data")
    )

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # --- CORS ---
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
