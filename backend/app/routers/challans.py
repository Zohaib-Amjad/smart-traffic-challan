"""Challan listing, creation, detail, status, deletion, PDF, and CSV APIs."""

import os
import io
import csv
import sqlite3
import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from app.config import DB_PATH, PDFS_DIR, EVIDENCE_DIR
from app.services.pdf_generator import generate_challan_pdf, generate_qr_code
from app.punjab_schedule import (
    DUE_DAYS_DEFAULT,
    lookup_fine,
    schedule_for_vehicle,
)
from app.routers.auth import require_roles

router = APIRouter(prefix="/api/challans", tags=["Challans"])

class GenerateChallanRequest(BaseModel):
    vehicle_number: str
    location: str
    violation_code: Optional[str] = None
    violation_name: Optional[str] = None
    fine_amount: Optional[int] = None
    issued_by: Optional[int] = None
    due_date: Optional[str] = None

class DisputeRequest(BaseModel):
    challan_no: str
    reason: str

class DisputeReviewRequest(BaseModel):
    status: str
    response: str = ""

class StatusUpdateRequest(BaseModel):
    status: str # Paid, Unpaid, Disputed
    payment_method: Optional[str] = None
    payment_ref: Optional[str] = None

@router.get("")
def get_challans(
    status: Optional[str] = None,
    plate: Optional[str] = None,
    issued_by: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(require_roles("Officer"))
):
    # Build a parameterized query so the history table supports safe filters.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
    SELECT c.*, v.owner_name, v.owner_phone, v.vehicle_make, v.vehicle_model, v.vehicle_type
    FROM challans c
    LEFT JOIN vehicles v ON c.plate_number = v.plate_number
    WHERE 1=1
    """
    params = []
    count_query = "SELECT COUNT(*) FROM challans WHERE 1=1"
    count_params = []

    query += " AND c.issued_by = ?"
    count_query += " AND issued_by = ?"
    params.append(user["id"])
    count_params.append(user["id"])
    
    if status and status.upper() != "ALL":
        query += " AND UPPER(c.status) = ?"
        count_query += " AND UPPER(status) = ?"
        params.append(status.upper())
        count_params.append(status.upper())
        
    if plate:
        query += " AND c.plate_number LIKE ?"
        count_query += " AND plate_number LIKE ?"
        plate_like = f"%{plate.strip().upper()}%"
        params.append(plate_like)
        count_params.append(plate_like)

    if issued_by is not None:
        query += " AND c.issued_by = ?"
        count_query += " AND issued_by = ?"
        params.append(issued_by)
        count_params.append(issued_by)
        
    query += " ORDER BY c.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    cursor.execute(count_query, count_params)
    total_count = cursor.fetchone()[0]
    conn.close()
    
    return {"total": total_count, "challans": [dict(row) for row in rows], "items": [dict(row) for row in rows]}

@router.get("/schedule")
def get_punjab_schedule(vehicle_type: Optional[str] = None, engine_cc: Optional[int] = None, _: dict = Depends(require_roles("Officer"))):
    """Punjab Twelfth Schedule: 25 offences priced for this vehicle class."""
    return schedule_for_vehicle(vehicle_type, engine_cc)

@router.get("/tariffs/list")
def get_violation_tariffs(vehicle_type: Optional[str] = None, engine_cc: Optional[int] = None, _: dict = Depends(require_roles("Officer"))):
    """Returns Punjab offences with the amount that applies to this vehicle class."""
    schedule = schedule_for_vehicle(vehicle_type or "Motor car", engine_cc)
    tariffs = []
    for item in schedule["violations"]:
        if not item["applicable"]:
            continue
        tariffs.append({
            "code": item["code"],
            "title": item["title"],
            "description": item["law_reference"],
            "fine_amount": item["amount"],
            "points": 2,
        })
    return {"tariffs": tariffs, **schedule}

@router.get("/plate/{plate_number}")
def get_challans_by_plate(plate_number: str, _: dict = Depends(require_roles("Officer"))):
    """
    CRUD Read: Fetch vehicle owner details and all associated challans by Number Plate.
    """
    clean_plate = plate_number.strip().upper()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Fetch Vehicle and Owner details
    cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (clean_plate,))
    veh = cursor.fetchone()
    
    # 2. Fetch all challans for this plate
    cursor.execute("""
    SELECT * FROM challans 
    WHERE plate_number = ?
    ORDER BY id DESC
    """, (clean_plate,))
    challan_rows = cursor.fetchall()
    conn.close()
    
    challans_list = [dict(r) for r in challan_rows]
    total_fine = sum(c["fine_amount"] for c in challans_list)
    unpaid_fine = sum(c["fine_amount"] for c in challans_list if c["status"].upper() in ["UNPAID", "PENDING"])
    paid_fine = sum(c["fine_amount"] for c in challans_list if c["status"].upper() == "PAID")
    
    return {
        "plate_number": clean_plate,
        "vehicle": dict(veh) if veh else None,
        "challans": challans_list,
        "summary": {
            "total_challans": len(challans_list),
            "unpaid_count": sum(1 for c in challans_list if c["status"].upper() in ["UNPAID", "PENDING"]),
            "paid_count": sum(1 for c in challans_list if c["status"].upper() == "PAID"),
            "total_fine": total_fine,
            "unpaid_fine": unpaid_fine,
            "paid_fine": paid_fine
        }
    }

@router.post("/generate")
def create_manual_challan(req: GenerateChallanRequest, user: dict = Depends(require_roles("Officer"))):
    # Manual officer entry follows the same database challan format as ANPR.
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Timestamp-based ticket number identifies this manual issue event.
    now = datetime.datetime.now()
    challan_no = f"CH-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    created_at_str = now.strftime("%Y-%m-%d %H:%M:%S")
    default_due = (now + datetime.timedelta(days=DUE_DAYS_DEFAULT)).date()
    if req.due_date:
        try:
            chosen_due = datetime.datetime.strptime(req.due_date.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            conn.close()
            raise HTTPException(status_code=400, detail="Payment due date must be a valid date.")
        if chosen_due < now.date():
            conn.close()
            raise HTTPException(status_code=400, detail="Payment due date cannot be in the past.")
        due_date_str = chosen_due.strftime("%Y-%m-%d")
    else:
        due_date_str = default_due.strftime("%Y-%m-%d")

    clean_plate = req.vehicle_number.strip().upper()
    cursor.execute(
        "SELECT vehicle_type, engine_cc FROM vehicles WHERE plate_number = ?",
        (clean_plate,),
    )
    vehicle_row = cursor.fetchone()
    vehicle_type = vehicle_row[0] if vehicle_row else "Motor car"
    engine_cc = vehicle_row[1] if vehicle_row else 1600

    offence = lookup_fine(req.violation_code or req.violation_name, vehicle_type, engine_cc)
    if not offence["violation_code"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Select a valid Punjab schedule offence.")
    if not offence["applicable"]:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"{offence['violation_name']} does not apply to {offence['fine_bracket_label']}.",
        )

    fine = offence["amount"]
    clean_v_name = offence["violation_name"]
    violation_code = offence["violation_code"]
    
    cursor.execute("""
    INSERT INTO challans 
    (challan_no, plate_number, location, violation_code, violation_name, fine_amount, status, created_at, due_date, issued_by)
    VALUES (?, ?, ?, ?, ?, ?, 'Unpaid', ?, ?, ?)
    """, (
        challan_no,
        clean_plate,
        req.location.strip(),
        violation_code,
        clean_v_name,
        fine,
        created_at_str,
        due_date_str,
        user["id"]
    ))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "id": new_id,
        "challan_no": challan_no,
        "plate_number": clean_plate,
        "violation_name": clean_v_name,
        "fine_amount": fine,
        "location": req.location.strip(),
        "status": "Unpaid",
        "created_at": created_at_str,
        "due_date": due_date_str
    }

@router.get("/export/csv")
def export_challans_csv(_: dict = Depends(require_roles("Officer"))):
    """Generates and downloads Microsoft Excel compatible CSV report."""
    # Export the complete history as a browser-downloadable CSV stream.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, plate_number, violation_name, fine_amount, location, status, created_at, due_date FROM challans ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Challan ID", "Vehicle Number", "Violation", "Fine Amount", "Location", "Status", "Issue Date", "Due/Expiry Date"])
    
    for r in rows:
        writer.writerow([r["id"], r["plate_number"], r["violation_name"], r["fine_amount"], r["location"] or "lahore", r["status"], r["created_at"], r["due_date"] or "N/A"])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=challan_report.csv"}
    )

@router.get("/disputes")
def list_disputes(_: dict = Depends(require_roles("Officer"))):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM challan_disputes ORDER BY id DESC").fetchall()
    conn.close()
    return {"disputes": [dict(row) for row in rows]}

@router.patch("/disputes/{dispute_id}")
def review_dispute(dispute_id: int, req: DisputeReviewRequest, user: dict = Depends(require_roles("Officer"))):
    status = req.status.strip().title()
    if status not in {"Open", "Accepted", "Rejected", "Resolved"}:
        raise HTTPException(status_code=400, detail="Invalid dispute status.")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("UPDATE challan_disputes SET status = ?, response = ?, reviewed_by = ?, resolved_at = ? WHERE id = ?", (status, req.response.strip(), user["id"], now if status in {"Accepted", "Rejected", "Resolved"} else None, dispute_id))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    if not changed:
        raise HTTPException(status_code=404, detail="Dispute not found.")
    return {"success": True, "status": status}

@router.get("/{challan_id_or_no}")
def get_challan_detail(challan_id_or_no: str, _: dict = Depends(require_roles("Officer"))):
    # Accept either the numeric database ID or the public challan number.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if challan_id_or_no.isdigit():
        cursor.execute("""
        SELECT c.*, v.owner_name, v.owner_cnic, v.owner_phone, v.owner_email, v.owner_address,
               v.vehicle_make, v.vehicle_model, v.vehicle_color, v.vehicle_type, v.engine_cc,
               v.registration_date, v.source
        FROM challans c
        LEFT JOIN vehicles v ON c.plate_number = v.plate_number
        WHERE c.id = ?
        """, (int(challan_id_or_no),))
    else:
        cursor.execute("""
        SELECT c.*, v.owner_name, v.owner_cnic, v.owner_phone, v.owner_email, v.owner_address,
               v.vehicle_make, v.vehicle_model, v.vehicle_color, v.vehicle_type, v.engine_cc,
               v.registration_date, v.source
        FROM challans c
        LEFT JOIN vehicles v ON c.plate_number = v.plate_number
        WHERE c.challan_no = ?
        """, (challan_id_or_no,))
        
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Challan record not found")
        
    return dict(row)

@router.patch("/{challan_id_or_no}/status")
def update_challan_status(challan_id_or_no: str, req: StatusUpdateRequest, _: dict = Depends(require_roles("Officer"))):
    """
    CRUD Update: Update challan payment status (e.g. Paid / Unpaid / Disputed).
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    where_clause = "id = ?" if challan_id_or_no.isdigit() else "challan_no = ?"
    val = int(challan_id_or_no) if challan_id_or_no.isdigit() else challan_id_or_no
    
    cursor.execute(f"SELECT challan_no, fine_amount, plate_number FROM challans WHERE {where_clause}", (val,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Challan not found")
        
    challan_no, fine_amount, plate_number = row
    
    if req.status.upper() == "PAID":
        cursor.execute(f"""
        UPDATE challans 
        SET status = 'Paid', paid_at = ?, payment_method = ?, payment_ref = ?
        WHERE {where_clause}
        """, (now_str, req.payment_method or "Counter / Cash", req.payment_ref or "OFFLINE-PAY", val))
    else:
        cursor.execute(f"""
        UPDATE challans 
        SET status = ?, paid_at = NULL
        WHERE {where_clause}
        """, (req.status, val))
        
    conn.commit()
    conn.close()
    
    return {"success": True, "message": f"Challan #{challan_no} status updated to {req.status}."}

@router.delete("/{challan_id_or_no}")
def delete_challan(challan_id_or_no: str, _: dict = Depends(require_roles("Officer"))):
    """
    CRUD Delete: Remove or cancel a challan record.
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    where_clause = "id = ?" if challan_id_or_no.isdigit() else "challan_no = ?"
    val = int(challan_id_or_no) if challan_id_or_no.isdigit() else challan_id_or_no
    
    cursor.execute(f"DELETE FROM challans WHERE {where_clause}", (val,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="Challan record not found.")
        
    return {"success": True, "message": "Challan record deleted successfully."}

@router.get("/{challan_no}/pdf")
def download_challan_pdf(challan_no: str, _: dict = Depends(require_roles("Officer"))):
    pdf_filename = generate_challan_pdf(challan_no)
    pdf_path = os.path.join(PDFS_DIR, pdf_filename) if pdf_filename else ""
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Could not generate PDF for this challan")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"E-Challan_{challan_no}.pdf",
    )

@router.get("/{challan_no}/qr")
def download_challan_qr(challan_no: str, _: dict = Depends(require_roles("Officer"))):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT challan_no FROM challans WHERE challan_no = ?", (challan_no,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Challan not found")
    qr_path = generate_qr_code(challan_no)
    return FileResponse(qr_path, media_type="image/png", filename=f"{challan_no}_qr.png")

@router.post("/dispute")
def dispute_challan(req: DisputeRequest, _: dict = Depends(require_roles("Officer"))):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM challans WHERE challan_no = ?", (req.challan_no,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Challan not found")
        
    cursor.execute("""
    UPDATE challans 
    SET status = 'Disputed', dispute_reason = ?
    WHERE challan_no = ?
    """, (req.reason, req.challan_no))
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Dispute filed successfully for review."}

