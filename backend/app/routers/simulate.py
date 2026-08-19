import os
import cv2
import base64
import numpy as np
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from app.anpr.detector import VehiclePlateDetector
from app.anpr.ocr_reader import extract_plate_number, preprocess_plate_image, clean_and_verify_plate_data
from app.anpr.tracker import VehicleTracker
from app.anpr.violation_rules import check_and_create_violations
from app.config import EVIDENCE_DIR

router = APIRouter(prefix="/api/simulate", tags=["Pipeline Processor & Simulation"])

detector = VehiclePlateDetector()
demo_tracker = VehicleTracker()

def mat_to_base64(image_mat):
    if image_mat is None or image_mat.size == 0:
        return ""
    _, buffer = cv2.imencode('.jpg', image_mat)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

@router.post("/process_image")
async def process_test_image(
    file: UploadFile = File(...),
    violation_type: str = Form("V-RED-LIGHT"),
    speed_simulated: int = Form(75)
):
    """
    Input Stage (Requirement #1): Upload Image Input.
    Executes full ANPR Pipeline:
    - Vehicle & Number Plate Detection (Req #2, #3)
    - OCR Text Extraction (Req #4)
    - Data Cleaning and Verification (Req #5)
    - Data Storage & Challan Generation (Req #6, #8)
    """
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image file format")
        
    h, w = frame.shape[:2]
    
    # 1. Preprocessing stage (Grayscale & Canny Edges)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(blur, 30, 200)
    
    # 2. Vehicle & Plate Detection
    detections = detector.process_frame(frame)
    annotated_frame = frame.copy()
    
    # Check if a valid plate was found
    if not detections or not detections[0].get("plate_number"):
        # NO PLATE DETECTED: Return empty real result (NO hardcoded fake plate)
        return {
            "success": False,
            "plate_number": "No number plate text detected.",
            "is_valid": False,
            "province": "Unknown",
            "confidence": 0.0,
            "pipeline_stages": {
                "original_image": mat_to_base64(frame),
                "edge_detection": mat_to_base64(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)),
                "plate_crop": "",
                "binary_threshold": "",
                "ai_annotated_frame": mat_to_base64(annotated_frame)
            },
            "violation_result": None
        }

    det = detections[0]
    plate_text = det["plate_number"]
    confidence = det["confidence"]
    plate_crop = det["plate_crop"]
    px, py, pw, ph = det["plate_bbox"]
    vx, vy, vw, vh = det["vehicle_bbox"]
    
    cv2.rectangle(annotated_frame, (vx, vy), (vx+vw, vy+vh), (0, 255, 0), 2)
    cv2.rectangle(annotated_frame, (px, py), (px+pw, py+ph), (0, 0, 255), 2)
    cv2.putText(annotated_frame, f"PLATE: {plate_text} ({int(confidence*100)}%)",
                (px, max(20, py-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
    # 3. Data Cleaning and Verification
    cleaned_info = clean_and_verify_plate_data(plate_text)
    
    # 4. Binary Thresholding
    thresh_plate = preprocess_plate_image(plate_crop) if plate_crop is not None else None
    
    # 5. Violation Check & Automatic Challan Generation
    mock_detection = [{
        "vehicle_bbox": (vx, vy, vw, vh),
        "plate_bbox": (px, py, pw, ph),
        "plate_crop": plate_crop,
        "plate_number": cleaned_info["plate"],
        "confidence": confidence,
        "vehicle_type": "Car"
    }]
    
    tracked = demo_tracker.update(mock_detection)
    tracked[0]["speed_kmh"] = speed_simulated
    
    cam_info = {
        "id": 1,
        "name": "Kalma Chowk Intersect #1",
        "location": "lahore",
        "speed_limit": 60,
        "signal_state": "RED" if violation_type == "V-RED-LIGHT" else "GREEN"
    }
    
    violations = check_and_create_violations(annotated_frame, tracked, cam_info, demo_tracker)
    
    return {
        "success": True,
        "plate_number": cleaned_info["plate"],
        "is_valid": cleaned_info["is_valid"],
        "province": cleaned_info["province"],
        "confidence": confidence,
        "pipeline_stages": {
            "original_image": mat_to_base64(frame),
            "edge_detection": mat_to_base64(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)),
            "plate_crop": mat_to_base64(plate_crop),
            "binary_threshold": mat_to_base64(cv2.cvtColor(thresh_plate, cv2.COLOR_GRAY2BGR)) if thresh_plate is not None else "",
            "ai_annotated_frame": mat_to_base64(annotated_frame)
        },
        "violation_result": violations[0] if violations else None
    }

@router.post("/process_video")
async def process_test_video(
    file: UploadFile = File(...),
    speed_limit: int = Form(60),
    signal_state: str = Form("RED")
):
    """
    Input Stage (Requirement #1): Upload Video Input (.mp4, .avi, .mov).
    Processes video stream frame-by-frame.
    """
    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)
    if not cap.isOpened():
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=400, detail="Could not open uploaded video stream.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 100
    
    video_tracker = VehicleTracker()
    detected_vehicles = []
    generated_violations = []
    
    cam_info = {
        "id": 1,
        "name": "Live Video Feed Camera",
        "location": "lahore",
        "speed_limit": speed_limit,
        "signal_state": signal_state.upper()
    }
    
    frame_idx = 0
    sample_annotated_frame = None
    
    while cap.isOpened() and frame_idx < min(300, total_frames):
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_idx += 1
        # Process every 5th frame for performance
        if frame_idx % 5 != 0:
            continue
            
        detections = detector.process_frame(frame)
        if detections:
            tracked = video_tracker.update(detections)
            v_list = check_and_create_violations(frame, tracked, cam_info, video_tracker)
            if v_list:
                generated_violations.extend(v_list)
            if sample_annotated_frame is None:
                sample_annotated_frame = frame.copy()

    cap.release()
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    return {
        "success": True,
        "frames_processed": frame_idx,
        "vehicles_tracked_count": len(video_tracker.tracked_vehicles),
        "violations_detected_count": len(generated_violations),
        "violations": generated_violations[:10],
        "preview_annotated_frame": mat_to_base64(sample_annotated_frame) if sample_annotated_frame is not None else ""
    }
