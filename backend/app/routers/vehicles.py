import sqlite3
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.config import DB_PATH

router = APIRouter(prefix="/api/vehicles", tags=["Vehicle Management"])

class VehicleAddRequest(BaseModel):
    plate_number: str
    vehicle_type: str
    owner_name: str
    vehicle_model: str
    vehicle_color: Optional[str] = "White"

@router.get("")
def list_vehicles():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicles ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return {"vehicles": [dict(r) for r in rows]}

@router.post("/add")
def add_vehicle(req: VehicleAddRequest):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        cursor.execute("""
        INSERT INTO vehicles 
        (plate_number, vehicle_type, owner_name, vehicle_model, vehicle_color, vehicle_make, registration_date, tax_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Paid')
        """, (
            req.plate_number.strip().upper(),
            req.vehicle_type,
            req.owner_name.strip(),
            req.vehicle_model.strip(),
            req.vehicle_color.strip() if req.vehicle_color else "White",
            req.vehicle_model.split()[0] if req.vehicle_model else "Vehicle",
            now_date
        ))
        conn.commit()
        vid = cursor.lastrowid
        conn.close()
        
        return {
            "success": True,
            "vehicle": {
                "id": vid,
                "plate_number": req.plate_number.strip().upper(),
                "vehicle_type": req.vehicle_type,
                "owner_name": req.owner_name,
                "vehicle_model": req.vehicle_model,
                "vehicle_color": req.vehicle_color or "White"
            }
        }
    except sqlite3.IntegrityError:
        # If exists, update
        cursor.execute("""
        UPDATE vehicles 
        SET vehicle_type = ?, owner_name = ?, vehicle_model = ?, vehicle_color = ?
        WHERE plate_number = ?
        """, (
            req.vehicle_type,
            req.owner_name.strip(),
            req.vehicle_model.strip(),
            req.vehicle_color.strip() if req.vehicle_color else "White",
            req.plate_number.strip().upper()
        ))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Vehicle updated successfully."}
