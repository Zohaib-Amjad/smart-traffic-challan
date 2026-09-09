"""SQLite connection helpers and the complete database schema."""

import sqlite3
import datetime
from pathlib import Path
from app.config import DB_PATH

def get_db():
    # Yield one connection to a caller and always close it afterward.
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    # CREATE IF NOT EXISTS makes startup safe for both new and existing databases.
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 1. Users: login identity and role used by the dashboard.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'Officer',
        created_at TEXT NOT NULL
    );
    """)
    
    # 2. Vehicles: registered plate and owner information.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number TEXT UNIQUE NOT NULL,
        owner_name TEXT NOT NULL,
        owner_cnic TEXT NOT NULL DEFAULT '35202-1234567-1',
        owner_phone TEXT NOT NULL DEFAULT '0300-1234567',
        owner_email TEXT,
        owner_address TEXT NOT NULL DEFAULT 'Lahore, Pakistan',
        vehicle_make TEXT NOT NULL,
        vehicle_model TEXT NOT NULL,
        vehicle_color TEXT NOT NULL,
        vehicle_type TEXT DEFAULT 'Car',
        registration_date TEXT,
        tax_status TEXT DEFAULT 'Paid',
        source TEXT DEFAULT 'user',
        source_image TEXT,
        plate_key TEXT
    );
    """)

    # Dataset photos mapped to OCR'd plate text for Number Plate Recognition.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS archive_images (
        image_name TEXT PRIMARY KEY,
        plate_number TEXT NOT NULL,
        plate_key TEXT NOT NULL,
        extra_plates TEXT DEFAULT '[]',
        file_hash TEXT,
        pixel_hash TEXT,
        bbox_json TEXT
    );
    """)
    
    # 3. Cameras: location, signal, speed limit, and active-state metadata.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cameras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        speed_limit INTEGER DEFAULT 60,
        signal_state TEXT DEFAULT 'GREEN', -- GREEN, YELLOW, RED
        is_active INTEGER DEFAULT 1,
        lat REAL,
        lng REAL
    );
    """)
    
    # 4. Tariffs: standard violation names, fines, and points.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS violation_tariffs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        fine_amount INTEGER NOT NULL,
        points INTEGER DEFAULT 2
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_types (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        fine_bracket TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS violations (
        code TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT,
        law_reference TEXT,
        sort_order INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        violation_code TEXT NOT NULL,
        fine_bracket TEXT NOT NULL,
        amount INTEGER,
        province TEXT NOT NULL DEFAULT 'Punjab',
        law_reference TEXT,
        effective_from TEXT,
        UNIQUE(violation_code, fine_bracket, province)
    );
    """)
    
    # 5. Challans: detected/manual offences and payment/evidence fields.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS challans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challan_no TEXT UNIQUE NOT NULL,
        plate_number TEXT NOT NULL,
        camera_id INTEGER,
        camera_name TEXT,
        location TEXT,
        violation_code TEXT NOT NULL,
        violation_name TEXT NOT NULL,
        fine_amount INTEGER NOT NULL,
        speed_detected INTEGER DEFAULT 0,
        speed_limit INTEGER DEFAULT 60,
        evidence_image TEXT,
        plate_crop TEXT,
        pdf_path TEXT,
        status TEXT DEFAULT 'Unpaid', -- Unpaid, Paid, Disputed
        created_at TEXT NOT NULL,
        due_date TEXT,
        paid_at TEXT,
        payment_method TEXT,
        payment_ref TEXT,
        dispute_reason TEXT,
        issued_by INTEGER,
        FOREIGN KEY (camera_id) REFERENCES cameras(id),
        FOREIGN KEY (issued_by) REFERENCES users(id)
    );
    """)
    
    # 6. Logs: an audit trail for important system events.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        description TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_ownership_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL,
        previous_owner_email TEXT,
        new_owner_email TEXT NOT NULL,
        verified_by INTEGER,
        transfer_reason TEXT,
        created_at TEXT NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL,
        document_type TEXT NOT NULL,
        document_ref TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        verified_by INTEGER,
        created_at TEXT NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS challan_disputes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challan_no TEXT NOT NULL,
        citizen_email TEXT NOT NULL,
        reason TEXT NOT NULL,
        response TEXT,
        status TEXT NOT NULL DEFAULT 'Open',
        reviewed_by INTEGER,
        created_at TEXT NOT NULL,
        resolved_at TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        read_at TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Keep older project databases compatible with the current schema.
    try:
        cursor.execute("ALTER TABLE challans ADD COLUMN due_date TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists

    issued_by_added = False
    try:
        cursor.execute("ALTER TABLE challans ADD COLUMN issued_by INTEGER")
        issued_by_added = True
    except sqlite3.OperationalError:
        pass  # column already exists

    # Existing tickets had no issuer; assign them to the demo officer once.
    if issued_by_added:
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ? LIMIT 1", ("officer@traffic.gov.pk",))
        officer = cursor.fetchone()
        if officer:
            cursor.execute(
                "UPDATE challans SET issued_by = ? WHERE issued_by IS NULL",
                (officer[0],),
            )

    for column, definition in (
        ("source", "TEXT DEFAULT 'user'"),
        ("source_image", "TEXT"),
        ("plate_key", "TEXT"),
        ("engine_cc", "INTEGER"),
        ("registration_status", "TEXT DEFAULT 'Active'"),
        ("ownership_verified", "INTEGER DEFAULT 1"),
    ):
        try:
            cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError:
            pass

    # Index frequently searched values so registry and challan lookups stay fast.
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_plate ON vehicles(plate_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_plate_key ON vehicles(plate_key);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_challans_plate ON challans(plate_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_challans_no ON challans(challan_no);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_challans_issued_by ON challans(issued_by);")
    for column, definition in (
        ("file_hash", "TEXT"),
        ("pixel_hash", "TEXT"),
        ("bbox_json", "TEXT"),
    ):
        try:
            cursor.execute(f"ALTER TABLE archive_images ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError:
            pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_file_hash ON archive_images(file_hash);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_archive_pixel_hash ON archive_images(pixel_hash);")
    
    conn.commit()
    conn.close()
