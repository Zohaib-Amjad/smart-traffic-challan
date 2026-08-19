import sqlite3
import datetime
from app.config import DB_PATH
from app.database import init_db

USERS_DATA = [
    {
        "name": "Traffic Officer",
        "email": "officer@traffic.gov.pk",
        "password": "admin123",
        "role": "Officer",
        "created_at": "2026-08-10 08:00:00"
    }
]

VEHICLES_DATA = [
    {
        "plate_number": "123",
        "owner_name": "Ahmed Khan",
        "owner_cnic": "35202-1234567-1",
        "owner_phone": "0300-1234567",
        "owner_email": "ahmed.khan@gmail.com",
        "owner_address": "Lahore, Pakistan",
        "vehicle_make": "Toyota",
        "vehicle_model": "Corolla",
        "vehicle_color": "Red",
        "vehicle_type": "Motorcycle",
        "registration_date": "2026-08-10",
        "tax_status": "Paid"
    },
    {
        "plate_number": "234",
        "owner_name": "Muhammad Ali",
        "owner_cnic": "35202-7654321-2",
        "owner_phone": "0300-7654321",
        "owner_email": "muhammad.ali@gmail.com",
        "owner_address": "Lahore, Pakistan",
        "vehicle_make": "Honda",
        "vehicle_model": "Civic",
        "vehicle_color": "White",
        "vehicle_type": "Car",
        "registration_date": "2026-08-10",
        "tax_status": "Paid"
    },
    {
        "plate_number": "LEA-21-4589",
        "owner_name": "Muhammad Usman Khan",
        "owner_cnic": "35202-8923411-3",
        "owner_phone": "+92 300 4589123",
        "owner_email": "usman.khan@gmail.com",
        "owner_address": "House 45-B, Sector C, Bahria Town, Lahore",
        "vehicle_make": "Honda",
        "vehicle_model": "Civic Oriel 2021",
        "vehicle_color": "Crystal Black",
        "vehicle_type": "Sedan",
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
        "vehicle_type": "Sedan",
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
        "vehicle_type": "Hatchback",
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
        "registration_date": "2023-08-01",
        "tax_status": "Paid"
    }
]

CAMERAS_DATA = [
    {
        "code": "CAM-01",
        "name": "Kalma Chowk Intersect #1",
        "location": "lahore",
        "speed_limit": 60,
        "signal_state": "RED",
        "is_active": 1,
        "lat": 31.5034,
        "lng": 74.3318
    },
    {
        "code": "CAM-02",
        "name": "Islamabad Expressway North",
        "location": "islamabad",
        "speed_limit": 80,
        "signal_state": "GREEN",
        "is_active": 1,
        "lat": 33.6844,
        "lng": 73.0479
    }
]

TARIFFS_DATA = [
    {
        "code": "V-SIGNAL",
        "title": "Signal Violation",
        "description": "Crossing intersection stop-line during RED traffic signal phase.",
        "fine_amount": 3000,
        "points": 3
    },
    {
        "code": "V-WRONG-PARKING",
        "title": "Wrong Parking",
        "description": "Unauthorized parking in no-parking zone.",
        "fine_amount": 2000,
        "points": 2
    },
    {
        "code": "V-RED-LIGHT",
        "title": "Red Light Signal Jumping",
        "description": "Crossing intersection stop-line during RED traffic signal phase.",
        "fine_amount": 2500,
        "points": 3
    },
    {
        "code": "V-OVERSPEED",
        "title": "Over-Speeding Violation",
        "description": "Exceeding designated road speed limit.",
        "fine_amount": 2000,
        "points": 2
    },
    {
        "code": "V-WRONG-WAY",
        "title": "Wrong Way / Illegal U-Turn",
        "description": "Driving against traffic flow or unauthorized U-turn.",
        "fine_amount": 3000,
        "points": 4
    }
]

CHALLANS_SEED = [
    {
        "challan_no": "CH-2026-0001",
        "plate_number": "123",
        "camera_id": 1,
        "camera_name": "Kalma Chowk Intersect #1",
        "location": "lahore",
        "violation_code": "V-SIGNAL",
        "violation_name": "Signal Violation",
        "fine_amount": 3000,
        "speed_detected": 45,
        "speed_limit": 60,
        "status": "Unpaid",
        "created_at": "2026-08-10 07:55:56"
    },
    {
        "challan_no": "CH-2026-0002",
        "plate_number": "234",
        "camera_id": 1,
        "camera_name": "Mall Road Crossing",
        "location": "lahore",
        "violation_code": "V-WRONG-PARKING",
        "violation_name": "Wrong Parking",
        "fine_amount": 2000,
        "speed_detected": 0,
        "speed_limit": 60,
        "status": "Unpaid",
        "created_at": "2026-08-10 08:06:06"
    },
    {
        "challan_no": "CH-2026-0003",
        "plate_number": "234",
        "camera_id": 1,
        "camera_name": "Gulberg Main Boulevard",
        "location": "lahore",
        "violation_code": "V-WRONG-PARKING",
        "violation_name": "Wrong Parking",
        "fine_amount": 2000,
        "speed_detected": 0,
        "speed_limit": 60,
        "status": "Unpaid",
        "created_at": "2026-08-10 08:06:21"
    }
]

def seed_database():
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Clean previous seed to ensure dummy replacement
    cursor.execute("DELETE FROM users WHERE email LIKE '%aleena%'")
    cursor.execute("DELETE FROM vehicles WHERE owner_name = 'aleena'")
    
    # 1. Seed Users
    for u in USERS_DATA:
        cursor.execute("""
        INSERT OR REPLACE INTO users (name, email, password, role, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (u["name"], u["email"], u["password"], u["role"], u["created_at"]))
        
    # 2. Seed Vehicles
    for v in VEHICLES_DATA:
        cursor.execute("""
        INSERT OR REPLACE INTO vehicles 
        (plate_number, owner_name, owner_cnic, owner_phone, owner_email, owner_address, vehicle_make, vehicle_model, vehicle_color, vehicle_type, registration_date, tax_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v["plate_number"], v["owner_name"], v["owner_cnic"], v["owner_phone"],
            v["owner_email"], v["owner_address"], v["vehicle_make"], v["vehicle_model"],
            v["vehicle_color"], v["vehicle_type"], v["registration_date"], v["tax_status"]
        ))
        
    # 3. Seed Cameras
    for c in CAMERAS_DATA:
        cursor.execute("""
        INSERT OR IGNORE INTO cameras (code, name, location, speed_limit, signal_state, is_active, lat, lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (c["code"], c["name"], c["location"], c["speed_limit"], c["signal_state"], c["is_active"], c["lat"], c["lng"]))
        
    # 4. Seed Tariffs
    for t in TARIFFS_DATA:
        cursor.execute("""
        INSERT OR REPLACE INTO violation_tariffs (code, title, description, fine_amount, points)
        VALUES (?, ?, ?, ?, ?)
        """, (t["code"], t["title"], t["description"], t["fine_amount"], t["points"]))
        
    # 5. Seed Initial Challans
    for ch in CHALLANS_SEED:
        cursor.execute("""
        INSERT OR IGNORE INTO challans
        (challan_no, plate_number, camera_id, camera_name, location, violation_code, violation_name, fine_amount, speed_detected, speed_limit, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ch["challan_no"], ch["plate_number"], ch["camera_id"], ch["camera_name"],
            ch["location"], ch["violation_code"], ch["violation_name"], ch["fine_amount"],
            ch["speed_detected"], ch["speed_limit"], ch["status"], ch["created_at"]
        ))
        
    conn.commit()
    conn.close()
    print("[Database] Seeded users, vehicles, cameras, tariffs, and dummy records.")

if __name__ == "__main__":
    seed_database()
