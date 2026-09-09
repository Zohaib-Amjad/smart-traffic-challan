"""Computer-vision plate detection using Haar, contours, and OCR."""

import cv2
import numpy as np
from app.anpr.ocr_reader import extract_plate_number

class VehiclePlateDetector:
    """
    Detector for locating vehicles and number plates in real-time camera frames.
    Uses multi-stage OpenCV morphological filters, edge detection, and contour analysis.
    """
    def __init__(self):
        # Haar is the first detector; the contour method below is the fallback.
        self.plate_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
            self.plate_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"[Detector] Cascade load notice: {e}")
            
    def detect_plate_contours(self, image):
        """
        Morphological aspect ratio & edge based license plate extraction.
        """
        # Edges and rectangular contours provide a model-free plate candidate list.
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        blur = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(blur, 30, 200)
        
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]
        
        plate_candidates = []
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.018 * peri, True)
            
            if len(approx) == 4:
                x, y, cw, ch = cv2.boundingRect(approx)
                aspect_ratio = cw / float(ch)
                if 0.8 <= aspect_ratio <= 8.0 and (cw * ch) > 800 and cw < (w * 0.95):
                    plate_crop = image[y:y+ch, x:x+cw]
                    plate_candidates.append({
                        "bbox": (x, y, cw, ch),
                        "crop": plate_crop,
                        "score": cv2.contourArea(c)
                    })
                    
        return plate_candidates

    @staticmethod
    def _box_iou(box_a, box_b):
        ax, ay, aw, ah = box_a
        bx, by, bw, bh = box_b
        x1 = max(ax, bx)
        y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw)
        y2 = min(ay + ah, by + bh)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = (aw * ah) + (bw * bh) - inter
        return inter / union if union else 0.0

    def _merge_boxes(self, boxes, iou_thresh=0.35):
        kept = []
        for box in sorted(boxes, key=lambda item: item[2] * item[3], reverse=True):
            if any(self._box_iou(box, existing) >= iou_thresh for existing in kept):
                continue
            kept.append(box)
        return kept

    def _haar_plates(self, image, x_offset=0, y_offset=0, min_neighbors=3, min_size=(40, 14)):
        if image is None or image.size == 0 or self.plate_cascade is None or self.plate_cascade.empty():
            return []
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        plates = self.plate_cascade.detectMultiScale(
            gray, scaleFactor=1.08, minNeighbors=min_neighbors, minSize=min_size
        )
        return [
            (int(x + x_offset), int(y + y_offset), int(pw), int(ph))
            for (x, y, pw, ph) in plates
        ]

    def locate_plate_regions(self, frame):
        """Return unique plate bounding boxes (Haar on full frame and columns, plus contours)."""
        if frame is None or frame.size == 0:
            return []
        height, width = frame.shape[:2]
        boxes = self._haar_plates(frame, min_neighbors=3)
        merged = self._merge_boxes(boxes)
        if len(merged) < 2:
            strip_pad = max(8, width // 40)
            for index in range(3):
                x0 = max(0, (width * index) // 3 - strip_pad)
                x1 = min(width, (width * (index + 1)) // 3 + strip_pad)
                boxes.extend(self._haar_plates(frame[:, x0:x1], x_offset=x0, min_neighbors=2))
            merged = self._merge_boxes(boxes)
        if len(merged) < 2:
            for cand in self.detect_plate_contours(frame):
                x, y, cw, ch = cand["bbox"]
                aspect = cw / float(ch) if ch else 0
                if aspect < 1.5 or aspect > 6.8:
                    continue
                if cw * ch < max(600, int(width * height * 0.0008)):
                    continue
                merged.append((int(x), int(y), int(cw), int(ch)))
            merged = self._merge_boxes(merged)
        return merged

    def locate_vehicle_regions(self, frame):
        """Find separate car-sized blobs so a row of vehicles is not treated as one scene."""
        if frame is None or frame.size == 0:
            return []
        height, width = frame.shape[:2]
        y0 = int(height * 0.12)
        roi = frame[y0:, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (11, 11), 0)
        edges = cv2.Canny(blur, 35, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 11))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        min_area = width * height * 0.035
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            y += y0
            if cw * ch < min_area or ch < height * 0.18 or cw < width * 0.12:
                continue
            if cw > width * 0.82:
                continue
            if ch > cw * 1.7:
                continue
            aspect = cw / float(ch)
            if aspect < 0.5 or aspect > 3.4:
                continue
            boxes.append((int(x), int(y), int(cw), int(ch)))
        return self._merge_boxes(boxes, iou_thresh=0.2)

    def analyze_scene(self, frame):
        plates = self.locate_plate_regions(frame)
        vehicles = self.locate_vehicle_regions(frame)
        return {
            "plate_regions": plates,
            "vehicle_regions": vehicles,
            "is_multiple": len(plates) >= 2 or len(vehicles) >= 2,
        }

    def process_frame(self, frame):
        """
        Processes a single video frame / image to find vehicles, plates and read OCR.
        Returns list of detected vehicles with bounding boxes, plate text and crops.
        """
        if frame is None or frame.size == 0:
            return []
            
        h, w = frame.shape[:2]
        detections = []
        regions = self.locate_plate_regions(frame)

        for (x, y, pw, ph) in regions[:3]:
            pad_x, pad_y = int(pw * 0.05), int(ph * 0.05)
            x1, y1 = max(0, x - pad_x), max(0, y - pad_y)
            x2, y2 = min(w, x + pw + pad_x), min(h, y + ph + pad_y)
            crop = frame[y1:y2, x1:x2]
            ocr_res = extract_plate_number(crop)
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
                "vehicle_type": "Car",
            })

        return detections
