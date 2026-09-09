"""Business rules that turn tracked detections into evidence-backed challans."""

import os
import cv2
import uuid
import datetime
import sqlite3
from app.config import DB_PATH, EVIDENCE_DIR
from app.services.pdf_generator import generate_challan_pdf

def check_and_create_violations(frame, detections, camera_info, tracker):
    """
    Evaluates traffic rules for detected vehicles and records any violation.
    Returns list of newly triggered challan objects.
    """
    # A single frame can contain multiple vehicles and therefore multiple results.
    created_violations = []
    h, w = frame.shape[:2]
    
    # Virtual stop-line position (e.g. at 65% height of frame)
    stop_line_y = int(h * 0.65)
    
    speed_limit = camera_info.get("speed_limit", 60)
    signal_state = camera_info.get("signal_state", "GREEN").upper()
    camera_id = camera_info.get("id", 1)
    camera_name = camera_info.get("name", "Intersection Camera")
    location = camera_info.get("location", "Main Road")
    
    for det in detections:
        track_id = det.get("track_id")
        plate_number = det.get("plate_number", "UNKNOWN")
        speed = det.get("speed_kmh", 45)
        vx, vy, vw, vh = det["vehicle_bbox"]
        cy = vy + vh // 2
        
        violation_type = None
        violation_name = None
        fine_amount = 0
        
        # Rule 1: red-light crossing is based on signal state and virtual stop line.
        if signal_state == "RED" and cy > stop_line_y:
            violation_type = "V-RED-LIGHT"
            violation_name = "Red Light Signal Jumping"
            fine_amount = 2500
            
        # Rule 2: issue speeding only when the reading exceeds the limit by 5 km/h.
        elif speed > (speed_limit + 5):
            violation_type = "V-OVERSPEED"
            violation_name = f"Over-Speeding ({speed} km/h in {speed_limit} km/h zone)"
            fine_amount = 2000
            
        if violation_type and tracker.can_generate_challan(track_id, plate_number):
            # Create a unique ticket and preserve visual proof for later review.
            challan_uuid = f"CH-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            # Annotate the frame so an officer can see why the ticket was issued.
            evidence_frame = frame.copy()
            # Draw red banner on evidence frame
            cv2.rectangle(evidence_frame, (0, 0), (w, 50), (0, 0, 180), -1)
            cv2.putText(evidence_frame, f"TRAFFIC VIOLATION DETECTED: {violation_name}", (15, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            # Draw vehicle & plate box
            cv2.rectangle(evidence_frame, (vx, vy), (vx + vw, vy + vh), (0, 0, 255), 3)
            px, py, pw, ph = det["plate_bbox"]
            cv2.rectangle(evidence_frame, (px, py), (px + pw, py + ph), (0, 255, 255), 2)
            cv2.putText(evidence_frame, f"PLATE: {plate_number}", (px, max(20, py - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            evidence_filename = f"{challan_uuid}_evidence.jpg"
            plate_crop_filename = f"{challan_uuid}_plate.jpg"
            
            evidence_path = os.path.join(EVIDENCE_DIR, evidence_filename)
            plate_path = os.path.join(EVIDENCE_DIR, plate_crop_filename)
            
            cv2.imwrite(evidence_path, evidence_frame)
            if det.get("plate_crop") is not None and det["plate_crop"].size > 0:
                cv2.imwrite(plate_path, det["plate_crop"])
            else:
                crop_slice = evidence_frame[max(0, py):min(h, py+ph), max(0, px):min(w, px+pw)]
                if crop_slice.size > 0:
                    cv2.imwrite(plate_path, crop_slice)
                else:
                    cv2.imwrite(plate_path, evidence_frame)
                
            now_dt = datetime.datetime.now()
            now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
            due_str = (now_dt + datetime.timedelta(days=15)).strftime("%Y-%m-%d")
            
            # Save vehicle/challan data in one database transaction.
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # Unknown plates receive a provisional owner until registry verification.
            cursor.execute("SELECT owner_name FROM vehicles WHERE plate_number = ?", (plate_number,))
            v_row = cursor.fetchone()
            if not v_row and plate_number != "UNKNOWN":
                cursor.execute("""
                INSERT INTO vehicles (plate_number, owner_name, owner_cnic, owner_phone, owner_address, vehicle_make, vehicle_model, vehicle_color)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plate_number, "Unregistered / Temporary Citizen", "35201-0000000-0",
                    "+92 300 0000000", "Pending Verification Address", "Sedan", "Vehicle", "White"
                ))
            
            cursor.execute("""
            INSERT INTO challans 
            (challan_no, plate_number, camera_id, camera_name, location, violation_code, violation_name, fine_amount, speed_detected, speed_limit, evidence_image, plate_crop, status, created_at, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Unpaid', ?, ?)
            """, (
                challan_uuid, plate_number, camera_id, camera_name, location,
                violation_type, violation_name, fine_amount, speed, speed_limit,
                evidence_filename, plate_crop_filename, now_str, due_str
            ))
            
            # Record the event for the dashboard activity feed and audit history.
            cursor.execute("""
            INSERT INTO system_logs (event_type, description, timestamp)
            VALUES (?, ?, ?)
            """, ("VIOLATION_RECORDED", f"Challan {challan_uuid} issued to {plate_number} for {violation_name}", now_str))
            
            conn.commit()
            
            # Fetch complete challan record for generating PDF
            cursor.execute("SELECT * FROM challans WHERE challan_no = ?", (challan_uuid,))
            challan_row = cursor.fetchone()
            conn.close()
            
            # Generate the printable challan after the database row exists.
            pdf_rel_path = generate_challan_pdf(challan_uuid)
            
            created_violations.append({
                "challan_no": challan_uuid,
                "plate_number": plate_number,
                "violation_name": violation_name,
                "fine_amount": fine_amount,
                "speed_detected": speed,
                "location": location,
                "created_at": now_str,
                "evidence_image": evidence_filename
            })
            
    return created_violations
