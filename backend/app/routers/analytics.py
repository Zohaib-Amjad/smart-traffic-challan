"""Dashboard aggregate queries for counters, charts, activity, and cameras."""

import sqlite3
import datetime
from fastapi import APIRouter, Depends
from app.config import DB_PATH
from app.routers.auth import require_roles

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/dashboard")
def get_dashboard_metrics(_: dict = Depends(require_roles("Officer"))):
    # Collect all dashboard widgets in one response to reduce browser requests.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. High-level counters for KPI cards.
    cursor.execute("SELECT COUNT(*) FROM challans")
    total_challans = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM challans WHERE status = 'PENDING'")
    pending_challans = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM challans WHERE status = 'PAID'")
    paid_challans = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(fine_amount), 0) FROM challans WHERE status = 'PAID'")
    total_revenue = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(fine_amount), 0) FROM challans WHERE status = 'PENDING'")
    pending_revenue = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    total_registered_vehicles = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cameras WHERE is_active = 1")
    active_cameras = cursor.fetchone()[0]
    
    # 2. Group violations for the dashboard doughnut chart.
    cursor.execute("""
    SELECT violation_name, COUNT(*) as count, SUM(fine_amount) as total_fines
    FROM challans
    GROUP BY violation_name
    ORDER BY count DESC
    """)
    violations_by_type = [dict(r) for r in cursor.fetchall()]
    
    # 3. Rank locations by number of recorded challans.
    cursor.execute("""
    SELECT location, COUNT(*) as count
    FROM challans
    GROUP BY location
    ORDER BY count DESC
    LIMIT 5
    """)
    top_locations = [dict(r) for r in cursor.fetchall()]
    
    # 4. Return the latest violations for the live feed.
    cursor.execute("""
    SELECT * FROM challans 
    ORDER BY id DESC LIMIT 6
    """)
    recent_challans = [dict(r) for r in cursor.fetchall()]
    
    # 5. Return recent audit events for system monitoring.
    cursor.execute("""
    SELECT * FROM system_logs 
    ORDER BY id DESC LIMIT 10
    """)
    recent_logs = [dict(r) for r in cursor.fetchall()]
    
    # 6. Include current camera state for the control panel.
    cursor.execute("SELECT * FROM cameras")
    cameras = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "stats": {
            "total_challans": total_challans,
            "pending_challans": pending_challans,
            "paid_challans": paid_challans,
            "total_revenue": total_revenue,
            "pending_revenue": pending_revenue,
            "total_vehicles": total_registered_vehicles,
            "active_cameras": active_cameras,
            "detection_accuracy": "96.4%"
        },
        "violations_by_type": violations_by_type,
        "top_locations": top_locations,
        "recent_challans": recent_challans,
        "recent_logs": recent_logs,
        "cameras": cameras
    }
