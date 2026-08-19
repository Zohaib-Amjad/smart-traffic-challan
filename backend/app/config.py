import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = BASE_DIR.parent / "frontend"
UPLOADS_DIR = BASE_DIR / "uploads"
EVIDENCE_DIR = UPLOADS_DIR / "evidence"
PDFS_DIR = UPLOADS_DIR / "challans_pdf"
SAMPLE_MEDIA_DIR = BASE_DIR / "sample_media"

# Create required directories
for d in [UPLOADS_DIR, EVIDENCE_DIR, PDFS_DIR, SAMPLE_MEDIA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{BASE_DIR / 'traffic_challan.db'}"
DB_PATH = BASE_DIR / "traffic_challan.db"

# Server Settings
HOST = "127.0.0.1"
PORT = 8000

# Police Dept info
POLICE_DEPT_NAME = "National Traffic Police & Highway Authority"
HOTLINE = "130 (Toll Free)"
SYSTEM_VERSION = "2.4.0-FYP"
