"""Citizen portal endpoints for searching, disputing, and paying challans."""

import os
import sqlite3
import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.config import DB_PATH
from app.services.pdf_generator import generate_challan_pdf
from app.routers.auth import require_roles

router = APIRouter(prefix="/api/citizen", tags=["Citizen Portal"])

class PaymentRequest(BaseModel):
    challan_no: str
    payment_method: str # JazzCash, EasyPaisa, DebitCard, 1Link
    account_number: str
    payer_name: Optional[str] = "Citizen"

class CitizenDisputeRequest(BaseModel):
    challan_no: str
    reason: str

@router.get("/search")
def search_citizen_records(query: str, user: dict = Depends(require_roles("Citizen"))):
    """
    Search vehicle records and challans by Plate Number or CNIC.
    """
    # Require a meaningful query before searching by plate, CNIC, or ticket.
    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
        
    cleaned_q = query.strip()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Find the vehicle directly, then try a challan number if needed.
    cursor.execute("""
        SELECT * FROM vehicles
        WHERE (plate_number LIKE ? OR owner_cnic LIKE ?)
          AND LOWER(COALESCE(owner_email, '')) = LOWER(?)
        LIMIT 1
    """, (f"%{cleaned_q}%", f"%{cleaned_q}%", user["email"]))
    veh = cursor.fetchone()

    if not veh:
        cursor.execute("""
        SELECT c.plate_number
        FROM challans c
        JOIN vehicles v ON v.plate_number = c.plate_number
        WHERE UPPER(c.challan_no) = UPPER(?)
          AND LOWER(COALESCE(v.owner_email, '')) = LOWER(?)
        LIMIT 1
        """, (cleaned_q, user["email"]))
        matching_challan = cursor.fetchone()
        if matching_challan:
            cursor.execute("SELECT * FROM vehicles WHERE plate_number = ? LIMIT 1", (matching_challan["plate_number"],))
            veh = cursor.fetchone()
    
    plate_to_search = veh["plate_number"] if veh else cleaned_q.upper()
    
    # 2. Return every challan and calculate paid/pending totals for the portal.
    cursor.execute("""
        SELECT c.* FROM challans c
        JOIN vehicles v ON v.plate_number = c.plate_number
        WHERE (c.plate_number = ? OR c.challan_no = ?)
          AND LOWER(COALESCE(v.owner_email, '')) = LOWER(?)
        ORDER BY c.id DESC
    """, (plate_to_search, cleaned_q, user["email"]))
    challan_rows = cursor.fetchall()
    
    conn.close()
    
    challans = [dict(r) for r in challan_rows]
    total_pending = sum(c["fine_amount"] for c in challans if c["status"].upper() not in ["PAID"])
    total_paid = sum(c["fine_amount"] for c in challans if c["status"].upper() == "PAID")
    
    return {
        "found": bool(veh or challans),
        "vehicle": dict(veh) if veh else None,
        "challans": challans,
        "summary": {
            "total_challans": len(challans),
            "pending_count": sum(1 for c in challans if c["status"].upper() not in ["PAID"]),
            "paid_count": sum(1 for c in challans if c["status"].upper() == "PAID"),
            "total_pending_amount": total_pending,
            "total_paid_amount": total_paid
        }
    }

@router.get("/challans")
def list_citizen_challans(user: dict = Depends(require_roles("Citizen"))):
    """Return challans attached to the authenticated citizen's vehicle records."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT c.*, v.owner_name, v.vehicle_make, v.vehicle_model, v.vehicle_type
        FROM challans c
        JOIN vehicles v ON v.plate_number = c.plate_number
        WHERE LOWER(COALESCE(v.owner_email, '')) = LOWER(?)
        ORDER BY c.id DESC
    """, (user["email"],)).fetchall()
    conn.close()
    return {"challans": [dict(row) for row in rows]}

@router.get("/notifications")
def list_notifications(user: dict = Depends(require_roles("Citizen"))):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM notifications WHERE LOWER(user_email) = LOWER(?) ORDER BY id DESC LIMIT 50",
        (user["email"],),
    ).fetchall()
    conn.close()
    return {"notifications": [dict(row) for row in rows]}

@router.post("/disputes")
def create_citizen_dispute(req: CitizenDisputeRequest, user: dict = Depends(require_roles("Citizen"))):
    reason = req.reason.strip()
    if len(reason) < 5:
        raise HTTPException(status_code=400, detail="Please provide a clear dispute reason.")
    conn = sqlite3.connect(str(DB_PATH))
    exists = conn.execute("""
        SELECT 1 FROM challans c JOIN vehicles v ON v.plate_number = c.plate_number
        WHERE c.challan_no = ? AND LOWER(COALESCE(v.owner_email, '')) = LOWER(?)
    """, (req.challan_no, user["email"])).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Challan not found for this citizen.")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO challan_disputes (challan_no, citizen_email, reason, created_at)
        VALUES (?, ?, ?, ?)
    """, (req.challan_no, user["email"], reason, now))
    conn.execute("UPDATE challans SET status = 'Disputed', dispute_reason = ? WHERE challan_no = ?", (reason, req.challan_no))
    conn.commit()
    conn.close()
    return {"success": True, "status": "Open", "message": "Dispute submitted for officer review."}

@router.post("/pay")
def pay_challan(req: PaymentRequest, user: dict = Depends(require_roles("Citizen"))):
    """
    Simulates digital payment for an outstanding E-Challan.
    """
    # This demo records a simulated payment and regenerates the PDF as Paid.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.* FROM challans c
        JOIN vehicles v ON v.plate_number = c.plate_number
        WHERE c.challan_no = ?
          AND LOWER(COALESCE(v.owner_email, '')) = LOWER(?)
    """, (req.challan_no, user["email"]))
    ch = cursor.fetchone()
    if not ch:
        conn.close()
        raise HTTPException(status_code=404, detail="Challan not found")
        
    if ch["status"].upper() == "PAID":
        conn.close()
        return {"status": "already_paid", "message": "This challan has already been paid."}
        
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tx_ref = f"{req.payment_method[:2].upper()}-{uuid.uuid4().hex[:8].upper()}"
    
    cursor.execute("""
    UPDATE challans 
    SET status = 'Paid', paid_at = ?, payment_method = ?, payment_ref = ?
    WHERE challan_no = ?
    """, (now_str, req.payment_method, tx_ref, req.challan_no))
    
    cursor.execute("""
    INSERT INTO system_logs (event_type, description, timestamp)
    VALUES (?, ?, ?)
    """, ("PAYMENT_RECEIVED", f"Challan {req.challan_no} fine of PKR {ch['fine_amount']:,} paid via {req.payment_method} (Ref: {tx_ref})", now_str))
    
    conn.commit()
    conn.close()
    
    # Regenerate PDF with updated PAID status
    generate_challan_pdf(req.challan_no)
    
    return {
        "status": "success",
        "message": f"Payment of PKR {ch['fine_amount']:,} received successfully via {req.payment_method}.",
        "receipt": {
            "challan_no": req.challan_no,
            "plate_number": ch["plate_number"],
            "amount_paid": ch["fine_amount"],
            "payment_method": req.payment_method,
            "transaction_ref": tx_ref,
            "paid_at": now_str
        }
    }
