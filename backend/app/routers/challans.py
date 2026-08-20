import os
import io
import csv
import sqlite3
import datetime
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from app.config import DB_PATH, PDFS_DIR, EVIDENCE_DIR
from app.services.pdf_generator import generate_challan_pdf

router = APIRouter(prefix="/api/challans", tags=["Challans"])

class GenerateChallanRequest(BaseModel):
    vehicle_number: str
    violation_name: str
    location: str
    fine_amount: Optional[int] = 2000

class DisputeRequest(BaseModel):
    challan_no: str
    reason: str

class StatusUpdateRequest(BaseModel):
    status: str # Paid, Unpaid, Disputed
    payment_method: Optional[str] = None
    payment_ref: Optional[str] = None

@router.get("")
def get_challans(
    status: Optional[str] = None,
    plate: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
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
    
    if status and status.upper() != "ALL":
        query += " AND UPPER(c.status) = ?"
        params.append(status.upper())
        
    if plate:
        query += " AND c.plate_number LIKE ?"
        params.append(f"%{plate.strip().upper()}%")
        
    query += " ORDER BY c.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM challans")
    total_count = cursor.fetchone()[0]
    conn.close()
    
    return {"total": total_count, "challans": [dict(row) for row in rows], "items": [dict(row) for row in rows]}

@router.get("/tariffs/list")
def get_violation_tariffs():
    """Returns available violation types and standard fine tariffs."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM violation_tariffs ORDER BY id ASC")
    tariffs = cursor.fetchall()
    conn.close()
    return {"tariffs": [dict(t) for t in tariffs]}

@router.get("/plate/{plate_number}")
def get_challans_by_plate(plate_number: str):
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
def create_manual_challan(req: GenerateChallanRequest):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Generate unique ticket number
    now = datetime.datetime.now()
    challan_no = f"CH-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    created_at_str = now.strftime("%Y-%m-%d %H:%M:%S")
    due_date_str = (now + datetime.timedelta(days=15)).strftime("%Y-%m-%d")
    
    fine = req.fine_amount
    # If fine not specified, derive from violation name
    if "3000" in req.violation_name or "Signal" in req.violation_name or "Wrong Way" in req.violation_name:
        fine = 3000
    elif "2000" in req.violation_name or "Parking" in req.violation_name or "Phone" in req.violation_name or "Tinted" in req.violation_name:
        fine = 2000
    elif "2500" in req.violation_name or "Speed" in req.violation_name or "Red Light" in req.violation_name:
        fine = 2500
    elif "1000" in req.violation_name or "Helmet" in req.violation_name or "Lane" in req.violation_name:
        fine = 1000
    elif "1500" in req.violation_name or "Triple" in req.violation_name or "Seatbelt" in req.violation_name:
        fine = 1500
        
    clean_v_name = req.violation_name.split("-")[0].strip()
    clean_plate = req.vehicle_number.strip().upper()
    
    cursor.execute("""
    INSERT INTO challans 
    (challan_no, plate_number, location, violation_code, violation_name, fine_amount, status, created_at, due_date)
    VALUES (?, ?, ?, 'V-MANUAL', ?, ?, 'Unpaid', ?, ?)
    """, (
        challan_no,
        clean_plate,
        req.location.strip(),
        clean_v_name,
        fine,
        created_at_str,
        due_date_str
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
def export_challans_csv():
    """Generates and downloads Microsoft Excel compatible CSV report."""
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

@router.get("/{challan_id_or_no}")
def get_challan_detail(challan_id_or_no: str):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if challan_id_or_no.isdigit():
        cursor.execute("""
        SELECT c.*, v.owner_name, v.owner_cnic, v.owner_phone, v.owner_email, v.owner_address,
               v.vehicle_make, v.vehicle_model, v.vehicle_color, v.vehicle_type
        FROM challans c
        LEFT JOIN vehicles v ON c.plate_number = v.plate_number
        WHERE c.id = ?
        """, (int(challan_id_or_no),))
    else:
        cursor.execute("""
        SELECT c.*, v.owner_name, v.owner_cnic, v.owner_phone, v.owner_email, v.owner_address,
               v.vehicle_make, v.vehicle_model, v.vehicle_color, v.vehicle_type
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
def update_challan_status(challan_id_or_no: str, req: StatusUpdateRequest):
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
def delete_challan(challan_id_or_no: str):
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
def download_challan_pdf(challan_no: str):
    pdf_filename = f"{challan_no}.pdf"
    pdf_path = os.path.join(PDFS_DIR, pdf_filename)
    
    if not os.path.exists(pdf_path):
        pdf_filename = generate_challan_pdf(challan_no)
        pdf_path = os.path.join(PDFS_DIR, pdf_filename)
        
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Could not generate PDF for this challan")
        
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"E-Challan_{challan_no}.pdf"
    )

@router.post("/dispute")
def dispute_challan(req: DisputeRequest):
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
