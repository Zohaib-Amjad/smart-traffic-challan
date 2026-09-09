"""Central configuration for paths, server settings, and department details."""

import os
from pathlib import Path

# Build paths relative to the backend folder so the app works from any cwd.
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = BASE_DIR.parent / "frontend"
UPLOADS_DIR = BASE_DIR / "uploads"
EVIDENCE_DIR = UPLOADS_DIR / "evidence"
PDFS_DIR = UPLOADS_DIR / "challans_pdf"
SAMPLE_MEDIA_DIR = BASE_DIR / "sample_media"
ARCHIVE_DIR = BASE_DIR.parent / "archive"
ARCHIVE_PLATES_JSON = APP_DIR / "data" / "archive_plates.json"

# Create storage folders automatically before uploads or PDFs are generated.
for d in [UPLOADS_DIR, EVIDENCE_DIR, PDFS_DIR, SAMPLE_MEDIA_DIR, ARCHIVE_PLATES_JSON.parent]:
    d.mkdir(parents=True, exist_ok=True)

# SQLite is intentionally file-based, so no separate database server is needed.
DATABASE_URL = f"sqlite:///{BASE_DIR / 'traffic_challan.db'}"
DB_PATH = BASE_DIR / "traffic_challan.db"

# Local development server settings used by the direct Python entry point.
HOST = "127.0.0.1"
PORT = 8000

# Values reused in the UI and generated challan documents.
POLICE_DEPT_NAME = "National Traffic Police & Highway Authority"
HOTLINE = "130 (Toll Free)"
SYSTEM_VERSION = "2.4.0-FYP"
