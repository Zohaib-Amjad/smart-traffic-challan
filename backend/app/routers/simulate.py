"""Manual image/video pipeline endpoints used to demonstrate ANPR processing."""

import os
import cv2
import base64
import numpy as np
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional

from app.anpr.detector import VehiclePlateDetector
from app.anpr.ocr_reader import extract_plate_number, preprocess_plate_image, clean_and_verify_plate_data
from app.anpr.tracker import VehicleTracker
from app.anpr.violation_rules import check_and_create_violations
from app.config import EVIDENCE_DIR
from app.services.archive_registry import (
    crop_plate_box,
    find_archive_sample,
    remember_archive_plate,
)
from app.routers.auth import require_roles

router = APIRouter(prefix="/api/simulate", tags=["Pipeline Processor & Simulation"])

detector = VehiclePlateDetector()
demo_tracker = VehicleTracker()
MULTIPLE_DETECTED = "Multiple vehicles detected"


def mat_to_base64(image_mat):
    # Convert an OpenCV image into a browser-ready data URL for pipeline previews.
    if image_mat is None or image_mat.size == 0:
        return ""
    _, buffer = cv2.imencode('.jpg', image_mat)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')


def _ambiguous_result(plate_label, annotated_frame, original_frame, edges=None, plate_crop=None, from_archive=False):
    return {
        "success": False,
        "plate_number": plate_label,
        "is_valid": False,
        "province": "Unknown",
        "confidence": 0.0,
        "from_archive": from_archive,
        "pipeline_stages": {
            "original_image": mat_to_base64(original_frame),
            "edge_detection": mat_to_base64(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)) if edges is not None else "",
            "plate_crop": mat_to_base64(plate_crop) if plate_crop is not None else "",
            "binary_threshold": "",
            "ai_annotated_frame": mat_to_base64(annotated_frame)
        },
        "violation_result": None
    }


def _draw_plate_boxes(frame, boxes, label=None):
    annotated = frame.copy()
    for (x, y, pw, ph) in boxes:
        cv2.rectangle(annotated, (x, y), (x + pw, y + ph), (0, 0, 255), 2)
    caption = label or (MULTIPLE_DETECTED if len(boxes) >= 2 else "")
    if caption:
        overlay = "MULTIPLE VEHICLES" if "multiple" in caption.lower() else caption.upper()
        cv2.putText(
            annotated,
            overlay,
            (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )
    return annotated

@router.post("/process_image")
async def process_test_image(
    file: UploadFile = File(...),
    violation_type: str = Form("V-RED-LIGHT"),
    speed_simulated: int = Form(75)
    , user: dict = Depends(require_roles("Citizen", "Officer", "Admin"))
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

    archive_hit = find_archive_sample(file.filename or "", contents, frame)
    if archive_hit and archive_hit.get("boxes"):
        archive_boxes = []
        plate_crop = None
        for box in archive_hit["boxes"]:
            crop, (x, y, pw, ph) = crop_plate_box(frame, box)
            archive_boxes.append((x, y, pw, ph))
            if crop is not None and plate_crop is None:
                plate_crop = crop
        if len(archive_boxes) >= 2:
            annotated_frame = _draw_plate_boxes(frame, archive_boxes, MULTIPLE_DETECTED)
            return _ambiguous_result(
                MULTIPLE_DETECTED, annotated_frame, frame, plate_crop=plate_crop, from_archive=True
            )
        annotated_frame = frame.copy()
        plate_text = ""
        for box in archive_hit["boxes"]:
            crop, (x, y, pw, ph) = crop_plate_box(frame, box)
            cv2.rectangle(annotated_frame, (x, y), (x + pw, y + ph), (0, 0, 255), 2)
            if crop is None:
                continue
            plate_crop = crop
            ocr_res = extract_plate_number(crop)
            if ocr_res.get("plate"):
                plate_text = ocr_res["plate"]
                break
        if plate_text:
            remember_archive_plate(archive_hit["image_name"], plate_text)
            cv2.putText(
                annotated_frame,
                f"PLATE: {plate_text}",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            return {
                "success": True,
                "plate_number": plate_text,
                "is_valid": True,
                "province": "Unknown",
                "confidence": 0.99,
                "from_archive": True,
                "pipeline_stages": {
                    "original_image": mat_to_base64(frame),
                    "edge_detection": "",
                    "plate_crop": mat_to_base64(plate_crop) if plate_crop is not None else "",
                    "binary_threshold": "",
                    "ai_annotated_frame": mat_to_base64(annotated_frame)
                },
                "violation_result": None
            }
        return _ambiguous_result(
            "Not found", annotated_frame, frame, plate_crop=plate_crop, from_archive=True
        )
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(blur, 30, 200)

    scene = detector.analyze_scene(frame)
    regions = scene["plate_regions"]
    if scene["is_multiple"]:
        boxes = regions or scene["vehicle_regions"]
        annotated_frame = _draw_plate_boxes(frame, boxes, MULTIPLE_DETECTED)
        return _ambiguous_result(MULTIPLE_DETECTED, annotated_frame, frame, edges=edges)

    detections = detector.process_frame(frame)
    annotated_frame = frame.copy()
    
    if not detections or not detections[0].get("plate_number"):
        if regions:
            annotated_frame = _draw_plate_boxes(frame, regions)
        return _ambiguous_result("Not found", annotated_frame, frame, edges=edges)

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
                
    # 3. Normalize OCR text and validate the registration format.
    cleaned_info = clean_and_verify_plate_data(plate_text)
    display_plate = cleaned_info["plate"] or plate_text
    
    # 4. Prepare the plate preview used to explain OCR preprocessing.
    thresh_plate = preprocess_plate_image(plate_crop) if plate_crop is not None else None
    
    # 5. Track the detection and apply traffic rules; valid offences create a challan.
    mock_detection = [{
        "vehicle_bbox": (vx, vy, vw, vh),
        "plate_bbox": (px, py, pw, ph),
        "plate_crop": plate_crop,
        "plate_number": display_plate,
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
    
    violations = []
    if user["role"] == "Officer":
        violations = check_and_create_violations(annotated_frame, tracked, cam_info, demo_tracker)
    
    return {
        "success": bool(display_plate),
        "plate_number": display_plate or "Not found",
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
    , _: dict = Depends(require_roles("Officer"))
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
        # Sampling every fifth frame keeps the demo responsive on ordinary hardware.
        if frame_idx % 5 != 0:
            continue
            
        # Each sampled frame follows the same detector, tracker, and rule pipeline.
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
