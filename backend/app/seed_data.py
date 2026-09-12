"""Reference data and startup initialization."""

import sqlite3
import datetime
from app.config import DB_PATH
from app.database import init_db
from app.punjab_schedule import seed_punjab_schedule
from app.services.archive_registry import import_archive_plates, index_archive_dataset, plate_key

USERS_DATA = [
    {
        "name": "Traffic Enforcement Officer",
        "email": "officer@traffic.gov.pk",
        "password": "admin123",
        "role": "Officer",
        "created_at": "2026-08-10 08:00:00"
    },
    {
        "name": "Traffic Patrol Officer",
        "email": "officer2@traffic.gov.pk",
        "password": "admin123",
        "role": "Officer",
        "created_at": "2026-08-10 08:00:00"
    },
    {
        "name": "Vehicle Registration Officer",
        "email": "admin@traffic.gov.pk",
        "password": "admin123",
        "role": "Admin",
        "created_at": "2026-08-10 08:00:00"
    }
]

VEHICLES_DATA = [
    {
        "plate_number": "LEA-21-4589",
        "owner_name": "Muhammad Usman Khan",
        "owner_cnic": "35202-8923411-3",
        "owner_phone": "+92 300 4589123",
        "owner_email": "citizen@test.pk",
        "owner_address": "House 45-B, Sector C, Bahria Town, Lahore",
        "vehicle_make": "Honda",
        "vehicle_model": "Civic Oriel 2021",
        "vehicle_color": "Crystal Black",
        "vehicle_type": "Motor car",
        "engine_cc": 1800,
        "registration_date": "2021-03-15",
        "tax_status": "Paid"
    },
    {
        "plate_number": "ICT-AB-567",
        "owner_name": "Hamza Ali Tariq",
        "owner_cnic": "61101-4458921-7",
        "owner_phone": "+92 321 9876543",
        "owner_email": "hamza.tariq@yahoo.com",
        "owner_address": "Apartment 12, Silver Oaks, F-10/4, Islamabad",
        "vehicle_make": "Toyota",
        "vehicle_model": "Corolla Grande 2022",
        "vehicle_color": "Super White",
        "vehicle_type": "Motor car",
        "engine_cc": 1800,
        "registration_date": "2022-06-20",
        "tax_status": "Paid"
    },
    {
        "plate_number": "KHI-8921",
        "owner_name": "Syed Farhan Ahmed",
        "owner_cnic": "42101-7712349-1",
        "owner_phone": "+92 333 1122334",
        "owner_email": "s.farhan@hotmail.com",
        "owner_address": "Flat 4-A, Block 7, Gulshan-e-Iqbal, Karachi",
        "vehicle_make": "Suzuki",
        "vehicle_model": "Alto VXR 2020",
        "vehicle_color": "Silky Silver",
        "vehicle_type": "Motor car",
        "engine_cc": 660,
        "registration_date": "2020-01-10",
        "tax_status": "Paid"
    },
    {
        "plate_number": "MN-776-LHR",
        "owner_name": "Bilal Shahid",
        "owner_cnic": "35201-9988776-5",
        "owner_phone": "+92 345 5544332",
        "owner_email": "bilal.s@gmail.com",
        "owner_address": "Street 9, Model Town, Lahore",
        "vehicle_make": "Yamaha",
        "vehicle_model": "YBR 125G 2023",
        "vehicle_color": "Racing Blue",
        "vehicle_type": "Motorcycle",
        "engine_cc": 125,
        "registration_date": "2023-04-12",
        "tax_status": "Paid"
    },
    {
        "plate_number": "ISB-309",
        "owner_name": "Ayesha Malik",
        "owner_cnic": "37405-1234567-2",
        "owner_phone": "+92 301 7766554",
        "owner_email": "ayesha.malik@outlook.com",
        "owner_address": "House 102, Street 33, G-11/2, Islamabad",
        "vehicle_make": "Kia",
        "vehicle_model": "Sportage AWD 2023",
        "vehicle_color": "Cherry Black",
        "vehicle_type": "SUV",
        "engine_cc": 1999,
        "registration_date": "2023-08-01",
        "tax_status": "Paid"
    },
    {
        "plate_number": "RWP-4421",
        "owner_name": "Tariq Mehmood",
        "owner_cnic": "37405-6677889-1",
        "owner_phone": "+92 313 4455667",
        "owner_email": "tariq.m@yahoo.com",
        "owner_address": "Commercial Market, Satellite Town, Rawalpindi",
        "vehicle_make": "Honda",
        "vehicle_model": "City 1.5 Aspire",
        "vehicle_color": "Urban Titanium",
        "vehicle_type": "Motor car",
        "engine_cc": 1500,
        "registration_date": "2021-11-05",
        "tax_status": "Paid"
    },
    {
        "plate_number": "PESH-8890",
        "owner_name": "Kamran Khan Bangash",
        "owner_cnic": "17301-2233445-5",
        "owner_phone": "+92 300 9988776",
        "owner_email": "kamran.bangash@gmail.com",
        "owner_address": "University Town, Peshawar",
        "vehicle_make": "Toyota",
        "vehicle_model": "Hilux Revo 2023",
        "vehicle_color": "Attitude Black",
        "vehicle_type": "Pickup",
        "engine_cc": 2800,
        "registration_date": "2023-01-20",
        "tax_status": "Paid"
    },
    {
        "plate_number": "123",
        "owner_name": "Ahmed Khan",
        "owner_cnic": "35202-1234567-1",
        "owner_phone": "0300-1234567",
        "owner_email": "ahmed.khan@gmail.com",
        "owner_address": "Gulberg III, Lahore, Pakistan",
        "vehicle_make": "Toyota",
        "vehicle_model": "Corolla 1.6 Altis",
        "vehicle_color": "Super Red",
        "vehicle_type": "Motor car",
        "engine_cc": 1600,
        "registration_date": "2024-01-10",
        "tax_status": "Paid"
    },
    {
        "plate_number": "234",
        "owner_name": "Muhammad Ali",
        "owner_cnic": "35202-7654321-2",
        "owner_phone": "0300-7654321",
        "owner_email": "muhammad.ali@gmail.com",
        "owner_address": "Mall Road, Lahore, Pakistan",
        "vehicle_make": "Honda",
        "vehicle_model": "Civic VTEC 2020",
        "vehicle_color": "Taffeta White",
        "vehicle_type": "Motor car",
        "engine_cc": 1800,
        "registration_date": "2020-05-18",
        "tax_status": "Paid"
    }
]

CAMERAS_DATA = [
    {
        "code": "CAM-01",
        "name": "Kalma Chowk Intersect #1",
        "location": "Lahore - Kalma Chowk",
        "speed_limit": 60,
        "signal_state": "RED",
        "is_active": 1,
        "lat": 31.5034,
        "lng": 74.3318
    },
    {
        "code": "CAM-02",
        "name": "Mall Road Crossing North",
        "location": "Lahore - Mall Road",
        "speed_limit": 50,
        "signal_state": "GREEN",
        "is_active": 1,
        "lat": 31.5580,
        "lng": 74.3270
    },
    {
        "code": "CAM-03",
        "name": "Islamabad Expressway North",
        "location": "Islamabad - Expressway",
        "speed_limit": 80,
        "signal_state": "GREEN",
        "is_active": 1,
        "lat": 33.6844,
        "lng": 73.0479
    },
    {
        "code": "CAM-04",
        "name": "Shahrah-e-Faisal Main Signal",
        "location": "Karachi - Shahrah-e-Faisal",
        "speed_limit": 70,
        "signal_state": "YELLOW",
        "is_active": 1,
        "lat": 24.8607,
        "lng": 67.0011
    }
]

TARIFFS_DATA = []  # Replaced by seed_punjab_schedule() on startup.

CHALLANS_SEED = [
    {
        "challan_no": "CH-2026-0001",
        "plate_number": "123",
        "camera_id": 1,
        "camera_name": "Kalma Chowk Intersect #1",
        "location": "Lahore - Kalma Chowk",
        "violation_code": "V-03",
        "violation_name": "Violation of traffic signals (electronic/manual)",
        "fine_amount": 5000,
        "speed_detected": 45,
        "speed_limit": 60,
        "status": "Unpaid",
        "created_at": "2026-08-10 07:55:56",
        "due_date": "2026-08-25"
    },
    {
        "challan_no": "CH-2026-0002",
        "plate_number": "234",
        "camera_id": 2,
        "camera_name": "Mall Road Crossing North",
        "location": "Lahore - Mall Road",
        "violation_code": "V-23",
        "violation_name": "Violation of parking rules",
        "fine_amount": 5000,
        "speed_detected": 0,
        "speed_limit": 50,
        "status": "Unpaid",
        "created_at": "2026-08-12 08:06:06",
        "due_date": "2026-08-27"
    },
    {
        "challan_no": "CH-2026-0003",
        "plate_number": "LEA-21-4589",
        "camera_id": 1,
        "camera_name": "Kalma Chowk Intersect #1",
        "location": "Lahore - Kalma Chowk",
        "violation_code": "V-01",
        "violation_name": "Exceeding prescribed speed limit",
        "fine_amount": 5000,
        "speed_detected": 78,
        "speed_limit": 60,
        "status": "Unpaid",
        "created_at": "2026-08-15 14:20:10",
        "due_date": "2026-08-30"
    },
    {
        "challan_no": "CH-2026-0004",
        "plate_number": "ICT-AB-567",
        "camera_id": 3,
        "camera_name": "Islamabad Expressway North",
        "location": "Islamabad - Expressway",
        "violation_code": "V-21",
        "violation_name": "Using handheld mobile phone while driving",
        "fine_amount": 5000,
        "speed_detected": 65,
        "speed_limit": 80,
        "status": "Paid",
        "created_at": "2026-08-16 11:30:00",
        "due_date": "2026-08-31"
    },
    {
        "challan_no": "CH-2026-0005",
        "plate_number": "MN-776-LHR",
        "camera_id": 1,
        "camera_name": "Kalma Chowk Intersect #1",
        "location": "Lahore - Kalma Chowk",
        "violation_code": "V-19",
        "violation_name": "Motorcycle without crash helmet",
        "fine_amount": 2000,
        "speed_detected": 40,
        "speed_limit": 60,
        "status": "Unpaid",
        "created_at": "2026-08-18 16:45:22",
        "due_date": "2026-09-02"
    },
    {
        "challan_no": "CH-2026-0006",
        "plate_number": "KHI-8921",
        "camera_id": 4,
        "camera_name": "Shahrah-e-Faisal Main Signal",
        "location": "Karachi - Shahrah-e-Faisal",
        "violation_code": "V-06",
        "violation_name": "Driving on the wrong side of the road",
        "fine_amount": 5000,
        "speed_detected": 35,
        "speed_limit": 70,
        "status": "Paid",
        "created_at": "2026-08-14 09:15:00",
        "due_date": "2026-08-29"
    }
]

# Keep seeded plate numbers separate so demo vehicles can be removed without
# touching vehicles registered through the application.
SEEDED_VEHICLE_PLATES = tuple(vehicle["plate_number"] for vehicle in VEHICLES_DATA)

def seed_database():
    # Create the schema and refresh reference data.
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Remove built-in demo citizen identities so public registration is the only route
    # to create a citizen account. Keep officer/admin demo accounts available.
    cursor.execute("DELETE FROM users WHERE email IN (?, ?, ?)", (
        "citizen@test.pk",
        "citizen@example.com",
        "demo.citizen@traffic.gov.pk",
    ))

    # Keep the local demo officer/admin identities available for role-based login.
    # Citizen accounts must be created via public registration only.
    for user in USERS_DATA:
        cursor.execute("""
        INSERT INTO users (name, email, password, role, created_at, is_verified, verification_token, verification_expires_at, email_verified_at)
        VALUES (?, ?, ?, ?, ?, 1, NULL, NULL, ?)
        ON CONFLICT(email) DO UPDATE SET
            name = excluded.name,
            password = excluded.password,
            role = excluded.role,
            is_verified = 1,
            verification_token = NULL,
            verification_expires_at = NULL,
            email_verified_at = excluded.email_verified_at
        """, (
            user["name"],
            user["email"],
            user["password"],
            user["role"],
            user["created_at"],
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
    
    # 1. Keep registry plates available for Check Owner / challan lookup.
    for v in VEHICLES_DATA:
        cursor.execute("""
        INSERT INTO vehicles (
            plate_number, owner_name, owner_cnic, owner_phone, owner_email, owner_address,
            vehicle_make, vehicle_model, vehicle_color, vehicle_type, engine_cc, registration_date, tax_status,
            source, plate_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'demo', ?)
        ON CONFLICT(plate_number) DO UPDATE SET
            owner_name = excluded.owner_name,
            owner_cnic = excluded.owner_cnic,
            owner_phone = excluded.owner_phone,
            owner_email = excluded.owner_email,
            owner_address = excluded.owner_address,
            vehicle_make = excluded.vehicle_make,
            vehicle_model = excluded.vehicle_model,
            vehicle_color = excluded.vehicle_color,
            vehicle_type = excluded.vehicle_type,
            engine_cc = excluded.engine_cc,
            registration_date = excluded.registration_date,
            tax_status = excluded.tax_status,
            plate_key = excluded.plate_key,
            source = COALESCE(vehicles.source, 'demo')
        WHERE COALESCE(vehicles.source, 'demo') IN ('demo', 'archive')
        """, (
            v["plate_number"].strip().upper(),
            v["owner_name"],
            v["owner_cnic"],
            v["owner_phone"],
            v["owner_email"],
            v["owner_address"],
            v["vehicle_make"],
            v["vehicle_model"],
            v["vehicle_color"],
            v["vehicle_type"],
            v.get("engine_cc"),
            v["registration_date"],
            v["tax_status"],
            plate_key(v["plate_number"]),
        ))

    # Map leftover short labels onto Punjab vehicle types.
    cursor.execute("""
        UPDATE vehicles SET vehicle_type = 'Motor car'
        WHERE LOWER(TRIM(vehicle_type)) IN ('car', 'car / sedan', 'sedan', 'hatchback')
    """)
    cursor.execute("""
        UPDATE vehicles SET vehicle_type = 'Motorcycle'
        WHERE LOWER(TRIM(vehicle_type)) IN ('bike', 'motorcycle / bike')
    """)
    cursor.execute("""
        UPDATE vehicles SET engine_cc = 1600
        WHERE engine_cc IS NULL
          AND LOWER(TRIM(vehicle_type)) IN ('motor car', 'jeep', 'suv', 'motor cab', 'private vehicle')
    """)
        
    # 2. Seed Cameras
    for c in CAMERAS_DATA:
        cursor.execute("""
        INSERT OR REPLACE INTO cameras (code, name, location, speed_limit, signal_state, is_active, lat, lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (c["code"], c["name"], c["location"], c["speed_limit"], c["signal_state"], c["is_active"], c["lat"], c["lng"]))
        
    # 3. Punjab Twelfth Schedule: 25 offences x 5 vehicle-class columns.
    seed_punjab_schedule(cursor)
        
    # 4. Challans are created only through the authenticated application workflows.
    imported = import_archive_plates(cursor)
    conn.commit()
    indexed = index_archive_dataset()
        
    conn.commit()
    conn.close()
    print(f"[Database] Seeded users, Punjab schedule, cameras, and demo challans; imported {imported} archive plate records; indexed {indexed} archive images.")

if __name__ == "__main__":
    seed_database()
