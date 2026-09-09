"""Report summary and CSV export endpoints."""

import io
import csv
import sqlite3
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.config import DB_PATH
from app.routers.auth import require_roles

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])

@router.get("/summary")
def get_reports_summary(_: dict = Depends(require_roles("Officer"))):
    # Compute totals and grouped records used by the reports page.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Total Challans
    cursor.execute("SELECT COUNT(*) FROM challans")
    total_challans = cursor.fetchone()[0]
    
    # 2. Total Fine
    cursor.execute("SELECT COALESCE(SUM(fine_amount), 0) FROM challans")
    total_fine = cursor.fetchone()[0]
    
    # 3. Paid Fine
    cursor.execute("SELECT COALESCE(SUM(fine_amount), 0) FROM challans WHERE LOWER(status) = 'paid'")
    paid_fine = cursor.fetchone()[0]
    
    # 4. Unpaid Fine
    cursor.execute("SELECT COALESCE(SUM(fine_amount), 0) FROM challans WHERE LOWER(status) != 'paid'")
    unpaid_fine = cursor.fetchone()[0]
    
    # 5. Challan Status Count
    cursor.execute("SELECT COUNT(*) FROM challans WHERE LOWER(status) = 'paid'")
    paid_challans = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM challans WHERE LOWER(status) != 'paid'")
    unpaid_challans = cursor.fetchone()[0]
    
    # 6. Violation Summary
    cursor.execute("""
    SELECT violation_name, COUNT(*) as count 
    FROM challans 
    GROUP BY violation_name 
    ORDER BY count DESC
    """)
    violation_summary = [dict(r) for r in cursor.fetchall()]
    
    # 7. Recent Challans
    cursor.execute("""
    SELECT id, plate_number as vehicle, violation_name as violation, fine_amount as fine, status, created_at as date
    FROM challans 
    ORDER BY id DESC 
    LIMIT 10
    """)
    recent_challans = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_challans": total_challans,
        "total_fine": total_fine,
        "paid_fine": paid_fine,
        "unpaid_fine": unpaid_fine,
        "paid_challans": paid_challans,
        "unpaid_challans": unpaid_challans,
        "violation_summary": violation_summary,
        "recent_challans": recent_challans
    }

@router.get("/csv")
def download_reports_csv(_: dict = Depends(require_roles("Officer"))):
    # Stream a spreadsheet-compatible CSV without creating a server-side file.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, plate_number, violation_name, fine_amount, location, status, created_at FROM challans ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Challan ID", "Vehicle Number", "Violation", "Fine Amount", "Location", "Status", "Date"])
    
    for r in rows:
        writer.writerow([r["id"], r["plate_number"], r["violation_name"], r["fine_amount"], r["location"] or "lahore", r["status"], r["created_at"]])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=challan_report.csv"}
    )
