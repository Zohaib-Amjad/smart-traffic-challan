import cv2
import numpy as np
from app.anpr.ocr_reader import extract_plate_number

class VehiclePlateDetector:
    """
    Detector for locating vehicles and number plates in real-time camera frames.
    Uses multi-stage OpenCV morphological filters, edge detection, and contour analysis.
    """
    def __init__(self):
        # Load Haar Cascade for Russian / European / Generic plates as baseline
        self.plate_cascade = None
        try:
            # OpenCV includes haarcascade for russian_plate_number
            cascade_path = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
            self.plate_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"[Detector] Cascade load warning: {e}")
            
    def detect_plate_contours(self, image):
        """
        Morphological aspect ratio & edge based license plate extraction.
        Works across diverse plates with high accuracy and 0 external dependencies.
        """
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 1. Bilateral filter to reduce noise while keeping edges sharp
        blur = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # 2. Canny Edge Detection
        edged = cv2.Canny(blur, 30, 200)
        
        # 3. Find contours
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]
        
        plate_candidates = []
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.018 * peri, True)
            
            # Look for rectangular shapes with 4 vertices
            if len(approx) == 4:
                x, y, cw, ch = cv2.boundingRect(approx)
                aspect_ratio = cw / float(ch)
                # Standard number plates have aspect ratio between 1.8 and 5.5
                if 1.8 <= aspect_ratio <= 5.5 and (cw * ch) > 800 and cw < (w * 0.8):
                    plate_crop = image[y:y+ch, x:x+cw]
                    plate_candidates.append({
                        "bbox": (x, y, cw, ch),
                        "crop": plate_crop,
                        "score": cv2.contourArea(c)
                    })
                    
        return plate_candidates

    def process_frame(self, frame):
        """
        Processes a single video frame / image to find vehicles, plates and read OCR.
        Returns list of detected vehicles with bounding boxes, plate text and crops.
        """
        if frame is None or frame.size == 0:
            return []
            
        h, w = frame.shape[:2]
        detections = []
        
        # Try Haar Cascade first if available
        cascade_detected = False
        if self.plate_cascade is not None and not self.plate_cascade.empty():
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            plates = self.plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 20))
            
            for (x, y, pw, ph) in plates:
                cascade_detected = True
                # Extract crop with slight padding
                pad_x, pad_y = int(pw * 0.05), int(ph * 0.05)
                x1, y1 = max(0, x - pad_x), max(0, y - pad_y)
                x2, y2 = min(w, x + pw + pad_x), min(h, y + ph + pad_y)
                crop = frame[y1:y2, x1:x2]
                
                ocr_res = extract_plate_number(crop)
                
                # Approximate vehicle bounding box enclosing the plate
                vx1 = max(0, x - int(pw * 1.5))
                vy1 = max(0, y - int(ph * 4.0))
                vx2 = min(w, x + int(pw * 2.5))
                vy2 = min(h, y + int(ph * 2.5))
                
                detections.append({
                    "vehicle_bbox": (vx1, vy1, vx2 - vx1, vy2 - vy1),
                    "plate_bbox": (x, y, pw, ph),
                    "plate_crop": crop,
                    "plate_number": ocr_res["plate"],
                    "confidence": ocr_res["confidence"],
                    "vehicle_type": "Car"
                })

        # If cascade did not find, use Contour Analysis
        if not detections:
            candidates = self.detect_plate_contours(frame)
            for cand in candidates[:3]: # top candidates
                x, y, cw, ch = cand["bbox"]
                crop = cand["crop"]
                ocr_res = extract_plate_number(crop)
                
                if ocr_res["plate"] != "UNKNOWN" and len(ocr_res["plate"]) >= 3:
                    vx1 = max(0, x - int(cw * 1.2))
                    vy1 = max(0, y - int(ch * 3.5))
                    vx2 = min(w, x + int(cw * 2.2))
                    vy2 = min(h, y + int(ch * 2.0))
                    
                    detections.append({
                        "vehicle_bbox": (vx1, vy1, vx2 - vx1, vy2 - vy1),
                        "plate_bbox": (x, y, cw, ch),
                        "plate_crop": crop,
                        "plate_number": ocr_res["plate"],
                        "confidence": ocr_res["confidence"],
                        "vehicle_type": "Car"
                    })
                    
        return detections
