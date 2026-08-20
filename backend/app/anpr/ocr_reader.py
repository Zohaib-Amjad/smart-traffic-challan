import re
import cv2
import numpy as np
import os
import shutil

# Optional Neural EasyOCR engine
_easyocr_reader = None
def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            # Load English and number recognition in memory
            _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        except Exception as e:
            print(f"[OCR] EasyOCR initialization notice: {e}")
            _easyocr_reader = False
    return _easyocr_reader if _easyocr_reader is not False else None

def preprocess_plate_image(image):
    """
    Step 4: Image Pre-processing for Optical Character Recognition (OCR).
    Converts to grayscale, removes noise via bilateral filtering, applies adaptive 
    Otsu thresholding, and morphological opening to isolate alphanumeric characters.
    """
    if image is None or image.size == 0:
        return None
        
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
        
    # Resize to standardized height for optimal OCR glyph reading
    h, w = gray.shape[:2]
    if h > 0:
        scale = 100.0 / h
        new_w = max(1, int(w * scale))
        gray = cv2.resize(gray, (new_w, 100), interpolation=cv2.INTER_CUBIC)
        
    # Contrast Limited Adaptive Histogram Equalization (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Bilateral noise filter
    filtered = cv2.bilateralFilter(enhanced, 11, 17, 17)
    
    # Otsu binary thresholding
    _, thresh = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Morphological clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    return cleaned

def clean_and_verify_plate_data(raw_text: str) -> dict:
    """
    Step 5: Data Cleaning and Verification.
    - Strips unwanted non-alphanumeric symbols and noise.
    - Standardizes uppercase formatting.
    - Verifies format against standard vehicle registration syntax.
    """
    if not raw_text:
        return {"plate": "", "is_valid": False, "province": "Unknown"}
        
    cleaned = re.sub(r'[^A-Z0-9\s\-]', '', raw_text.upper()).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    province = "Punjab"
    if any(p in cleaned for p in ["ICT", "ISB", "ISLAMABAD"]):
        province = "Islamabad"
    elif any(p in cleaned for p in ["KHI", "SINDH", "KARACHI"]):
        province = "Sindh"
    elif any(p in cleaned for p in ["PEW", "KPK", "PESHAWAR"]):
        province = "KPK"
    elif any(p in cleaned for p in ["QTA", "BALOCHISTAN"]):
        province = "Balochistan"
        
    tokens = cleaned.replace('-', ' ').split()
    tokens = [t for t in tokens if len(t) > 0 and t not in ["PAKISTAN", "PUNJAB", "SINDH", "KPK", "ISLAMABAD"]]
    
    final_plate = " ".join(tokens) if tokens else cleaned
    
    is_valid = bool(len(final_plate) >= 3 and any(c.isdigit() for c in final_plate))
    
    return {
        "plate": final_plate if is_valid else (final_plate or ""),
        "raw": raw_text,
        "is_valid": is_valid,
        "province": province
    }

def extract_plate_number(plate_crop) -> dict:
    """
    Step 4: OCR Text Extraction.
    Uses Tesseract OCR with EasyOCR fallback.
    Returns empty/invalid if no alphanumeric plate text is present in the image.
    """
    if plate_crop is None or plate_crop.size == 0:
        return {
            "plate": "",
            "confidence": 0.0,
            "is_valid": False,
            "province": "Unknown",
            "engine": "None"
        }
        
    # Preprocess crop
    preprocessed = preprocess_plate_image(plate_crop)
    
    # 1. Attempt Tesseract OCR with layouts suitable for one- and two-line plates.
    try:
        import pytesseract
        if not shutil.which("tesseract"):
            for path in (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ):
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break

        if shutil.which("tesseract") or os.path.exists(pytesseract.pytesseract.tesseract_cmd):
            ocr_images = [plate_crop]
            if preprocessed is not None:
                ocr_images.append(preprocessed)
            for angle in (-15, 15):
                height, width = plate_crop.shape[:2]
                center = (width / 2, height / 2)
                matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(plate_crop, matrix, (width, height), borderMode=cv2.BORDER_REPLICATE)
                ocr_images.append(rotated)
                rotated_preprocessed = preprocess_plate_image(rotated)
                if rotated_preprocessed is not None:
                    ocr_images.append(rotated_preprocessed)

            for image in ocr_images:
                for psm in (6, 11, 12, 13, 7):
                    custom_config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- '
                    tess_text = pytesseract.image_to_string(image, config=custom_config)
                    cleaned_res = clean_and_verify_plate_data(tess_text)
                    if cleaned_res["is_valid"] and len(cleaned_res["plate"]) >= 3:
                        return {
                            "plate": cleaned_res["plate"],
                            "confidence": 0.93,
                            "is_valid": True,
                            "province": cleaned_res["province"],
                            "engine": "Tesseract OCR"
                        }
    except Exception as e:
        pass

    # 2. Attempt EasyOCR
    reader = get_easyocr_reader()
    if reader is not None:
        try:
            results = reader.readtext(plate_crop)
            if results:
                texts = []
                confidences = []
                for bbox, text, conf in results:
                    sanitized = re.sub(r'[^A-Z0-9\- ]', '', text.upper()).strip()
                    if sanitized and len(sanitized) >= 2:
                        texts.append(sanitized)
                        confidences.append(conf)
                        
                if texts:
                    full_raw = " ".join(texts)
                    cleaned_res = clean_and_verify_plate_data(full_raw)
                    if cleaned_res["is_valid"] or len(cleaned_res["plate"]) >= 2:
                        avg_conf = sum(confidences) / len(confidences)
                        return {
                            "plate": cleaned_res["plate"],
                            "confidence": round(avg_conf, 2),
                            "is_valid": cleaned_res["is_valid"],
                            "province": cleaned_res["province"],
                            "engine": "EasyOCR / Neural OCR"
                        }
        except Exception as e:
            pass

    # 3. If genuinely no text found, return NO detection (NO hardcoded fallback)
    return {
        "plate": "",
        "confidence": 0.0,
        "is_valid": False,
        "province": "Unknown",
        "engine": "None"
    }
