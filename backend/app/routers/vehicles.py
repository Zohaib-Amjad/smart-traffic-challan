"""CRUD endpoints for the registered vehicle and owner registry."""

import sqlite3
import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.config import DB_PATH
from app.services.archive_registry import get_or_create_dummy_vehicle, lookup_vehicle_row, plate_key
from app.routers.auth import require_roles

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

class OwnershipTransferRequest(BaseModel):
    new_owner_email: str
    reason: str = "Ownership transfer"

class VehicleDocumentRequest(BaseModel):
    document_type: str
    document_ref: str

class RegistrationStatusRequest(BaseModel):
    status: str

@router.get("")
def list_vehicles(_: dict = Depends(require_roles("Officer", "Admin"))):
    # List officer-registered vehicles; dataset plates stay available for lookup only.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM vehicles WHERE COALESCE(source, 'user') = 'user' ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"vehicles": [dict(r) for r in rows]}

@router.get("/search")
def search_registry(query: str, _: dict = Depends(require_roles("Admin", "Officer"))):
    query = query.strip()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Search requires at least two characters.")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM vehicles
        WHERE plate_number LIKE ? OR owner_name LIKE ? OR owner_cnic LIKE ?
        ORDER BY id DESC LIMIT 50
    """, (f"%{query.upper()}%", f"%{query}%", f"%{query}%")).fetchall()
    conn.close()
    return {"vehicles": [dict(row) for row in rows]}

@router.get("/{plate_number}/history")
def vehicle_history(plate_number: str, _: dict = Depends(require_roles("Admin", "Officer"))):
    clean_plate = plate_number.strip().upper()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    vehicle = conn.execute("SELECT * FROM vehicles WHERE plate_number = ?", (clean_plate,)).fetchone()
    history = conn.execute("SELECT * FROM vehicle_ownership_history WHERE vehicle_id = (SELECT id FROM vehicles WHERE plate_number = ?) ORDER BY id DESC", (clean_plate,)).fetchall()
    documents = conn.execute("SELECT * FROM vehicle_documents WHERE vehicle_id = (SELECT id FROM vehicles WHERE plate_number = ?) ORDER BY id DESC", (clean_plate,)).fetchall()
    conn.close()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    return {"vehicle": dict(vehicle), "ownership_history": [dict(row) for row in history], "documents": [dict(row) for row in documents]}

@router.post("/{plate_number}/transfer")
def transfer_ownership(plate_number: str, req: OwnershipTransferRequest, user: dict = Depends(require_roles("Admin"))):
    new_email = req.new_owner_email.strip().lower()
    if "@" not in new_email:
        raise HTTPException(status_code=400, detail="Enter a valid owner email.")
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT id, owner_email FROM vehicles WHERE plate_number = ?", (plate_number.strip().upper(),)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE vehicles SET owner_email = ?, ownership_verified = 0 WHERE id = ?", (new_email, row[0]))
    conn.execute("INSERT INTO vehicle_ownership_history (vehicle_id, previous_owner_email, new_owner_email, verified_by, transfer_reason, created_at) VALUES (?, ?, ?, ?, ?, ?)", (row[0], row[1], new_email, user["id"], req.reason.strip(), now))
    conn.commit()
    conn.close()
    return {"success": True, "status": "Pending verification", "owner_email": new_email}

@router.post("/{plate_number}/documents")
def add_vehicle_document(plate_number: str, req: VehicleDocumentRequest, _: dict = Depends(require_roles("Admin"))):
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT id FROM vehicles WHERE plate_number = ?", (plate_number.strip().upper(),)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO vehicle_documents (vehicle_id, document_type, document_ref, created_at) VALUES (?, ?, ?, ?)", (row[0], req.document_type.strip(), req.document_ref.strip(), now))
    conn.commit()
    conn.close()
    return {"success": True, "status": "Pending"}

@router.patch("/{plate_number}/documents/{document_id}")
def verify_vehicle_document(plate_number: str, document_id: int, req: RegistrationStatusRequest, user: dict = Depends(require_roles("Admin"))):
    status = req.status.strip().title()
    if status not in {"Verified", "Rejected", "Pending"}:
        raise HTTPException(status_code=400, detail="Document status must be Verified, Rejected, or Pending.")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE vehicle_documents SET status = ?, verified_by = ?
        WHERE id = ? AND vehicle_id = (SELECT id FROM vehicles WHERE plate_number = ?)
    """, (status, user["id"] if status == "Verified" else None, document_id, plate_number.strip().upper()))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    if not changed:
        raise HTTPException(status_code=404, detail="Document not found for this vehicle.")
    return {"success": True, "status": status}

@router.patch("/{plate_number}/status")
def update_registration_status(plate_number: str, req: RegistrationStatusRequest, _: dict = Depends(require_roles("Admin"))):
    status = req.status.strip().title()
    if status not in {"Active", "Suspended", "Blocked"}:
        raise HTTPException(status_code=400, detail="Status must be Active, Suspended, or Blocked.")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("UPDATE vehicles SET registration_status = ? WHERE plate_number = ?", (status, plate_number.strip().upper()))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    if not changed:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    return {"success": True, "registration_status": status}

@router.get("/{plate_number}")
def get_vehicle_by_plate(plate_number: str, _: dict = Depends(require_roles("Citizen", "Officer", "Admin"))):
    """
    CRUD Read: Fetch vehicle and owner details for a given number plate.
    """
    # Normalize user/OCR input before performing an exact registry lookup.
    clean_plate = plate_number.strip().upper()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        row = get_or_create_dummy_vehicle(cursor, clean_plate)
        conn.commit()
    except sqlite3.IntegrityError:
        row = lookup_vehicle_row(cursor, clean_plate)
        conn.rollback()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Enter at least 4 letters or digits to look up an owner.")
        
    return dict(row)

@router.post("/add")
def add_vehicle(req: VehicleAddRequest, _: dict = Depends(require_roles("Admin"))):
    """
    CRUD Create/Upsert: Add a new registered vehicle with owner details.
    """
    # Insert a new registration, or update it when the plate already exists.
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    clean_plate = req.plate_number.strip().upper()
    make = req.vehicle_make or (req.vehicle_model.split()[0] if req.vehicle_model else "Vehicle")
    
    try:
        cursor.execute("""
        INSERT INTO vehicles 
        (plate_number, vehicle_type, owner_name, owner_cnic, owner_phone, owner_email, owner_address, vehicle_make, vehicle_model, vehicle_color, registration_date, tax_status, source, plate_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Paid', 'user', ?)
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
            now_date,
            plate_key(clean_plate)
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
        SET vehicle_type = ?, owner_name = ?, owner_cnic = ?, owner_phone = ?, owner_email = ?, owner_address = ?, vehicle_make = ?, vehicle_model = ?, vehicle_color = ?, plate_key = ?, source = COALESCE(source, 'user')
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
            plate_key(clean_plate),
            clean_plate
        ))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Vehicle updated successfully."}

@router.put("/{plate_number}")
def update_vehicle(plate_number: str, req: VehicleUpdateRequest, _: dict = Depends(require_roles("Admin"))):
    """
    CRUD Update: Update vehicle/owner information.
    """
    # Only fields supplied by the client are applied to the existing record.
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
def delete_vehicle(plate_number: str, _: dict = Depends(require_roles("Admin"))):
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
