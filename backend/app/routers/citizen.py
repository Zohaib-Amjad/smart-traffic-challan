import os
import sqlite3
import datetime
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.config import DB_PATH
from app.services.pdf_generator import generate_challan_pdf

router = APIRouter(prefix="/api/citizen", tags=["Citizen Portal"])

class PaymentRequest(BaseModel):
    challan_no: str
    payment_method: str # JazzCash, EasyPaisa, DebitCard, 1Link
    account_number: str
    payer_name: Optional[str] = "Citizen"

@router.get("/search")
def search_citizen_records(query: str):
    """
    Search vehicle records and challans by Plate Number or CNIC.
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
        
    cleaned_q = query.strip()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Look up vehicle
    cursor.execute("""
    SELECT * FROM vehicles 
    WHERE plate_number LIKE ? OR owner_cnic LIKE ?
    LIMIT 1
    """, (f"%{cleaned_q}%", f"%{cleaned_q}%"))
    veh = cursor.fetchone()

    if not veh:
        cursor.execute("""
        SELECT plate_number FROM challans
        WHERE UPPER(challan_no) = UPPER(?)
        LIMIT 1
        """, (cleaned_q,))
        matching_challan = cursor.fetchone()
        if matching_challan:
            cursor.execute("SELECT * FROM vehicles WHERE plate_number = ? LIMIT 1", (matching_challan["plate_number"],))
            veh = cursor.fetchone()
    
    plate_to_search = veh["plate_number"] if veh else cleaned_q.upper()
    
    # 2. Look up all challans for this vehicle
    cursor.execute("""
    SELECT * FROM challans 
    WHERE plate_number = ? OR challan_no = ?
    ORDER BY id DESC
    """, (plate_to_search, cleaned_q))
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

@router.post("/pay")
def pay_challan(req: PaymentRequest):
    """
    Simulates digital payment for an outstanding E-Challan.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM challans WHERE challan_no = ?", (req.challan_no,))
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
