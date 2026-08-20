import sqlite3
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.config import DB_PATH

router = APIRouter(prefix="/api/vehicles", tags=["Vehicle Management"])

class VehicleAddRequest(BaseModel):
    plate_number: str
    vehicle_type: str = "Car"
    owner_name: str
    owner_cnic: Optional[str] = "35202-1234567-1"
    owner_phone: Optional[str] = "0300-1234567"
    owner_email: Optional[str] = None
    owner_address: Optional[str] = "Lahore, Pakistan"
    vehicle_make: Optional[str] = None
    vehicle_model: str
    vehicle_color: Optional[str] = "White"

class VehicleUpdateRequest(BaseModel):
    owner_name: Optional[str] = None
    owner_cnic: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    owner_address: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_color: Optional[str] = None

@router.get("")
def list_vehicles():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicles ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return {"vehicles": [dict(r) for r in rows]}

@router.get("/{plate_number}")
def get_vehicle_by_plate(plate_number: str):
    """
    CRUD Read: Fetch vehicle and owner details for a given number plate.
    """
    clean_plate = plate_number.strip().upper()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (clean_plate,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Vehicle not found in registry.")
        
    return dict(row)

@router.post("/add")
def add_vehicle(req: VehicleAddRequest):
    """
    CRUD Create/Upsert: Add a new registered vehicle with owner details.
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    clean_plate = req.plate_number.strip().upper()
    make = req.vehicle_make or (req.vehicle_model.split()[0] if req.vehicle_model else "Vehicle")
    
    try:
        cursor.execute("""
        INSERT INTO vehicles 
        (plate_number, vehicle_type, owner_name, owner_cnic, owner_phone, owner_email, owner_address, vehicle_make, vehicle_model, vehicle_color, registration_date, tax_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Paid')
        """, (
            clean_plate,
            req.vehicle_type,
            req.owner_name.strip(),
            req.owner_cnic or "35202-1234567-1",
            req.owner_phone or "0300-1234567",
            req.owner_email,
            req.owner_address or "Lahore, Pakistan",
            make,
            req.vehicle_model.strip(),
            req.vehicle_color.strip() if req.vehicle_color else "White",
            now_date
        ))
        conn.commit()
        vid = cursor.lastrowid
        conn.close()
        
        return {
            "success": True,
            "vehicle": {
                "id": vid,
                "plate_number": clean_plate,
                "vehicle_type": req.vehicle_type,
                "owner_name": req.owner_name,
                "owner_cnic": req.owner_cnic,
                "owner_phone": req.owner_phone,
                "owner_address": req.owner_address,
                "vehicle_make": make,
                "vehicle_model": req.vehicle_model,
                "vehicle_color": req.vehicle_color or "White"
            }
        }
    except sqlite3.IntegrityError:
        # If exists, update
        cursor.execute("""
        UPDATE vehicles 
        SET vehicle_type = ?, owner_name = ?, owner_cnic = ?, owner_phone = ?, owner_email = ?, owner_address = ?, vehicle_make = ?, vehicle_model = ?, vehicle_color = ?
        WHERE plate_number = ?
        """, (
            req.vehicle_type,
            req.owner_name.strip(),
            req.owner_cnic or "35202-1234567-1",
            req.owner_phone or "0300-1234567",
            req.owner_email,
            req.owner_address or "Lahore, Pakistan",
            make,
            req.vehicle_model.strip(),
            req.vehicle_color.strip() if req.vehicle_color else "White",
            clean_plate
        ))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Vehicle updated successfully."}

@router.put("/{plate_number}")
def update_vehicle(plate_number: str, req: VehicleUpdateRequest):
    """
    CRUD Update: Update vehicle/owner information.
    """
    clean_plate = plate_number.strip().upper()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (clean_plate,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Vehicle not found.")
        
    updates = []
    params = []
    
    if req.owner_name is not None:
        updates.append("owner_name = ?")
        params.append(req.owner_name.strip())
    if req.owner_cnic is not None:
        updates.append("owner_cnic = ?")
        params.append(req.owner_cnic.strip())
    if req.owner_phone is not None:
        updates.append("owner_phone = ?")
        params.append(req.owner_phone.strip())
    if req.owner_email is not None:
        updates.append("owner_email = ?")
        params.append(req.owner_email.strip())
    if req.owner_address is not None:
        updates.append("owner_address = ?")
        params.append(req.owner_address.strip())
    if req.vehicle_type is not None:
        updates.append("vehicle_type = ?")
        params.append(req.vehicle_type.strip())
    if req.vehicle_make is not None:
        updates.append("vehicle_make = ?")
        params.append(req.vehicle_make.strip())
    if req.vehicle_model is not None:
        updates.append("vehicle_model = ?")
        params.append(req.vehicle_model.strip())
    if req.vehicle_color is not None:
        updates.append("vehicle_color = ?")
        params.append(req.vehicle_color.strip())
        
    if updates:
        params.append(clean_plate)
        query = f"UPDATE vehicles SET {', '.join(updates)} WHERE plate_number = ?"
        cursor.execute(query, params)
        conn.commit()
        
    conn.close()
    return {"success": True, "message": "Vehicle updated successfully."}

@router.delete("/{plate_number}")
def delete_vehicle(plate_number: str):
    """
    CRUD Delete: Delete vehicle from registry.
    """
    clean_plate = plate_number.strip().upper()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM vehicles WHERE plate_number = ?", (clean_plate,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found in registry.")
        
    return {"success": True, "message": f"Vehicle {clean_plate} deleted successfully."}
