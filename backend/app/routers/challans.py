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
    
    return {"total": total_count, "items": [dict(row) for row in rows]}

@router.post("/generate")
def create_manual_challan(req: GenerateChallanRequest):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Generate unique ticket number
    now = datetime.datetime.now()
    challan_no = f"CH-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    created_at_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    fine = req.fine_amount
    # If fine not specified, derive from violation name
    if "3000" in req.violation_name or "Signal" in req.violation_name or "Wrong Way" in req.violation_name:
        fine = 3000
    elif "2000" in req.violation_name or "Parking" in req.violation_name:
        fine = 2000
    elif "2500" in req.violation_name or "Speed" in req.violation_name:
        fine = 2500
    elif "1000" in req.violation_name or "Helmet" in req.violation_name:
        fine = 1000
        
    clean_v_name = req.violation_name.split("-")[0].strip()
    
    cursor.execute("""
    INSERT INTO challans 
    (challan_no, plate_number, location, violation_code, violation_name, fine_amount, status, created_at)
    VALUES (?, ?, ?, 'V-MANUAL', ?, ?, 'Unpaid', ?)
    """, (
        challan_no,
        req.vehicle_number.strip().upper(),
        req.location.strip(),
        clean_v_name,
        fine,
        created_at_str
    ))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "id": new_id,
        "challan_no": challan_no,
        "plate_number": req.vehicle_number.strip().upper(),
        "violation_name": clean_v_name,
        "fine_amount": fine,
        "location": req.location.strip(),
        "status": "Unpaid",
        "created_at": created_at_str
    }

@router.get("/export/csv")
def export_challans_csv():
    """Generates and downloads Microsoft Excel compatible CSV report."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, plate_number, violation_name, fine_amount, location, status, created_at FROM challans ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Exact header from Screenshot 31
    writer.writerow(["Challan ID", "Vehicle Number", "Violation", "Fine Amount", "Location", "Status", "Date"])
    
    for r in rows:
        writer.writerow([r["id"], r["plate_number"], r["violation_name"], r["fine_amount"], r["location"] or "lahore", r["status"], r["created_at"]])
        
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
    
    # Check if integer ID or string Challan No
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
    SET status = 'DISPUTED', dispute_reason = ?
    WHERE challan_no = ?
    """, (req.reason, req.challan_no))
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Dispute filed successfully for review."}
