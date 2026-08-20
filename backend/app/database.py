import sqlite3
import datetime
from pathlib import Path
from app.config import DB_PATH

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 1. Users Table (for Authentication & Dashboard)
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
    
    # 2. Vehicles Registry
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
        tax_status TEXT DEFAULT 'Paid'
    );
    """)
    
    # 3. Traffic Cameras & Locations
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
    
    # 4. Violation Tariffs (Fines)
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
    
    # 5. Challans
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
        FOREIGN KEY (camera_id) REFERENCES cameras(id)
    );
    """)
    
    # 6. System Activity Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        description TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    # Safe migration for existing DB files (add due_date column if missing)
    try:
        cursor.execute("ALTER TABLE challans ADD COLUMN due_date TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Create Indexes for fast lookup by plate number and challan number
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_plate ON vehicles(plate_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_challans_plate ON challans(plate_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_challans_no ON challans(challan_no);")
    
    conn.commit()
    conn.close()
