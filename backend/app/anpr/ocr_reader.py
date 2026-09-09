"""OCR preprocessing, engine fallback, plate normalization, and validation."""

import re
import time
import cv2
import numpy as np
import os
import shutil

TESSERACT_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-. "
TESSERACT_CONFIG = (
    f"--oem 3 --psm {{psm}} "
    f"-c tessedit_char_whitelist={TESSERACT_WHITELIST}"
    f" -c preserve_interword_spaces=1"
)

NOISE_TOKENS = frozenset({
    "PAKISTAN", "PUNJAB", "SINDH", "KPK", "ISLAMABAD", "KARACHI", "PESHAWAR",
    "BALOCHISTAN", "VIRGINIA", "TEXAS", "FLORIDA", "OHIO", "NEVADA", "OREGON",
    "ARIZONA", "GEORGIA", "ALABAMA", "ALASKA", "HAWAII", "KANSAS", "MAINE",
    "IDAHO", "GARDEN", "STATE", "SUNSHINE", "MOUNTAIN", "MNE",
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "JUNE", "JULY", "AUGUST",
    "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
})

# Optional Neural EasyOCR engine
_easyocr_reader = None
def get_easyocr_reader():
    # Lazy loading avoids the heavy EasyOCR startup cost when Tesseract works.
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
    # Return no image for an invalid crop so callers can handle it gracefully.
    if image is None or image.size == 0:
        return None

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Resize to standardized height for optimal OCR glyph reading
    h, w = gray.shape[:2]
    if h > 0:
        scale = 120.0 / h
        new_w = max(1, int(w * scale))
        gray = cv2.resize(gray, (new_w, 120), interpolation=cv2.INTER_CUBIC)

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


def plate_ocr_views(image):
    """Full plate first, then inner band, then a left-trim for artwork-heavy plates."""
    if image is None or image.size == 0:
        return []
    views = [image]
    height, width = image.shape[:2]
    top = int(height * 0.12)
    bottom = max(top + 8, int(height * 0.88))
    left_margin = int(width * 0.04)
    right_margin = max(left_margin + 16, int(width * 0.96))
    if bottom - top >= 12 and right_margin - left_margin >= 24:
        views.append(image[top:bottom, left_margin:right_margin])
    artwork_left = int(width * 0.22)
    if width - artwork_left >= 40:
        views.append(image[top:bottom, artwork_left:right_margin])
    return views


def apply_ocr_digit_confusions(text: str) -> str:
    """Fix 8/S, 0/O, 1/I mix-ups without removing spaces, hyphens, or dots."""
    cleaned = (text or "").upper()
    cleaned = cleaned.replace(",", ".").replace("·", ".")
    cleaned = re.sub(r"(^|[\s\-])S(?=[\d.])", lambda match: match.group(1) + "8", cleaned)
    cleaned = re.sub(r"(^|[\s\-])O(?=[\d.])", lambda match: match.group(1) + "0", cleaned)
    cleaned = re.sub(r"(?<=\d)O(?=[\d.])", "0", cleaned)
    cleaned = re.sub(r"(^|[\s\-])[IL](?=\d)", lambda match: match.group(1) + "1", cleaned)
    cleaned = re.sub(r"(?<=\d)[IL](?=[\d.\s\-A-Z]|$)", "1", cleaned)
    cleaned = re.sub(r"(?<=\d)(?:UI|IU|IL|LI|UJ)(?=[A-Z])", "11", cleaned)
    cleaned = re.sub(r"(^|[\s\-])(\d{3})11([A-Z])(?=$|[\s\-])", r"\1\2.11\3", cleaned)
    return cleaned


def _rebuild_split_characters(tokens):
    rebuilt = []
    for token in tokens:
        if (
            len(token) == 1
            and rebuilt
            and len(rebuilt[-1]) >= 1
            and "-" not in rebuilt[-1]
            and "." not in rebuilt[-1]
            and (
                (token.isalpha() and rebuilt[-1].isalpha())
                or (token.isdigit() and rebuilt[-1].isdigit())
            )
        ):
            rebuilt[-1] += token
        else:
            rebuilt.append(token)
    return rebuilt


def format_common_layouts(text: str) -> str:
    """Keep separators the plate actually uses (space, hyphen, dot)."""
    spaced = re.sub(r"\s+", " ", (text or "").strip())
    spaced = re.sub(r"^[\s.\-]+|[\s.\-]+$", "", spaced)
    spaced = re.sub(r"\s*-\s*", "-", spaced)
    spaced = re.sub(r"\s*\.\s*", ".", spaced)
    spaced = spaced.strip("-. ")
    compact = re.sub(r"[^A-Z0-9]", "", spaced)

    uk = re.fullmatch(r"([A-Z]{2})(\d{2})([A-Z]{3})", compact)
    if uk:
        return f"{uk.group(1)}{uk.group(2)} {uk.group(3)}"

    euro_region = re.fullmatch(r"([A-Z]{2})([A-Z]{2})(\d{2,4})", compact)
    if euro_region:
        return f"{euro_region.group(1)} {euro_region.group(2)} {euro_region.group(3)}"

    dotted = re.sub(r"\s+", "", spaced)
    if re.fullmatch(r"[A-Z0-9]*\d+\.\d+[A-Z0-9]*", dotted):
        return dotted
    if re.fullmatch(r"\d{3}11[A-Z]", compact):
        return f"{compact[:3]}.11{compact[-1]}"

    if "-" in spaced:
        return spaced

    pk_city_year = re.fullmatch(r"([A-Z]{2,4})(\d{2})(\d{4})", compact)
    if pk_city_year:
        return f"{pk_city_year.group(1)}-{pk_city_year.group(2)}-{pk_city_year.group(3)}"

    pk_letters_digits = re.fullmatch(r"([A-Z]{2,4})(\d{4})", compact)
    if pk_letters_digits:
        return f"{pk_letters_digits.group(1)} {pk_letters_digits.group(2)}"

    return spaced


def clean_and_verify_plate_data(raw_text: str) -> dict:
    """
    Step 5: Data Cleaning and Verification.
    Keeps capital letters, digits, hyphens, dots, and spaces exactly as a plate shows them.
    """
    if not raw_text:
        return {"plate": "", "is_valid": False, "province": "Unknown", "raw": ""}

    cleaned = re.sub(r"[^A-Z0-9.\s\-]", " ", raw_text.upper())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = apply_ocr_digit_confusions(cleaned)

    province = "Punjab"
    if any(token in cleaned for token in ["ICT", "ISB", "ISLAMABAD"]):
        province = "Islamabad"
    elif any(token in cleaned for token in ["KHI", "SINDH", "KARACHI"]):
        province = "Sindh"
    elif any(token in cleaned for token in ["PEW", "KPK", "PESHAWAR"]):
        province = "KPK"
    elif any(token in cleaned for token in ["QTA", "BALOCHISTAN"]):
        province = "Balochistan"

    tokens = [token for token in cleaned.split() if token and token not in NOISE_TOKENS]
    tokens = [token for token in tokens if re.search(r"[A-Z0-9]", token)]
    tokens = _rebuild_split_characters(tokens)

    if len(tokens) >= 2 and tokens[0].isalpha() and tokens[1].isdigit() and len(tokens[1]) == 6:
        tokens[1:2] = [tokens[1][:2], tokens[1][2:]]

    final_plate = format_common_layouts(" ".join(tokens) if tokens else cleaned)

    pk_valid = bool(
        re.fullmatch(r"[A-Z]{2,4} \d{4}", final_plate)
        or re.fullmatch(r"[A-Z]{2,4} \d{1,2} \d{4}", final_plate)
        or re.fullmatch(r"[A-Z]{2,4}-\d{2}-\d{4}", final_plate)
        or re.fullmatch(r"[A-Z]{2,4}-\d{4}", final_plate)
    )
    uk_valid = bool(re.fullmatch(r"[A-Z]{2}\d{2} [A-Z]{3}", final_plate))
    dotted_valid = bool(re.fullmatch(r"[A-Z0-9]*\d+\.\d+[A-Z0-9]*", final_plate))
    compact = re.sub(r"[^A-Z0-9]", "", final_plate)
    has_digit = bool(re.search(r"\d", compact))
    plate_out = ""
    if has_digit and 3 <= len(compact) <= 15:
        plate_out = final_plate

    return {
        "plate": plate_out,
        "raw": raw_text,
        "is_valid": bool(plate_out) and (pk_valid or uk_valid or dotted_valid or has_digit),
        "province": province,
    }

def plate_candidate_score(plate: str) -> int:
    """Prefer complete alphanumeric readings over short partial OCR matches."""
    tokens = plate.split()
    alphanumeric_length = len(re.sub(r"[^A-Z0-9]", "", plate))
    score = alphanumeric_length * 2 + len(tokens)
    if re.fullmatch(r"[A-Z]{2}\d{2} [A-Z]{3}", plate):
        score += 120
    if re.search(r"\d+\.\d+", plate):
        score += 40
    if "-" in plate:
        score += 12
    if len(tokens) >= 3 and tokens[-1].isdigit() and len(tokens[-1]) >= 4:
        score += 8
    if len(tokens) >= 2 and tokens[0].isalpha() and len(tokens[0]) >= 2:
        score += 4
    if len(tokens) >= 3 and tokens[1].isdigit() and len(tokens[1]) == 2:
        score += 6
    if re.search(r"\b[A-Z]{2,4}\s+\d{1,2}\s+\d{4}\b", plate):
        score += 100
    elif re.search(r"\b[A-Z]{2,4}\s+\d{4}\b", plate):
        score += 90
    elif re.fullmatch(r"[A-Z]{2,4}-\d{2}-\d{4}", plate):
        score += 100
    elif alphanumeric_length > 14:
        score -= 40
    return score

def recover_partial_plate_text(raw_text: str) -> str:
    """Recover a common OCR loss: a leading zero in a four-digit serial."""
    normalized = re.sub(r"[^A-Z0-9\s]", " ", raw_text.upper())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    match = re.search(r"([A-Z]{2,5})\s+(\d{3})(?:\s+([A-Z]+))?", normalized)
    if not match:
        return ""
    if len(match.group(1)) <= 4 and not match.group(3):
        return ""
    letters = match.group(1)[-3:] if len(match.group(1)) > 4 else match.group(1)
    digits = match.group(2)
    if len(letters) < 2:
        return ""
    return f"{letters} 0{digits}"


def _tesseract_ready():
    try:
        import pytesseract
    except Exception:
        return None
    tesseract_paths = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    )
    installed_tesseract = next((path for path in tesseract_paths if os.path.isfile(path)), None)
    if installed_tesseract:
        pytesseract.pytesseract.tesseract_cmd = installed_tesseract
    if installed_tesseract or shutil.which("tesseract"):
        return pytesseract
    return None


def _read_with_tesseract(pytesseract, image, psm, timeout_sec):
    try:
        return pytesseract.image_to_string(
            image,
            config=TESSERACT_CONFIG.format(psm=psm),
            timeout=timeout_sec,
        )
    except Exception:
        return ""


def extract_plate_number(plate_crop, refinement_depth: int = 0) -> dict:
    """
    Step 4: OCR Text Extraction.
    Uses Tesseract OCR with EasyOCR fallback.
    Returns empty/invalid if no alphanumeric plate text is present in the image.
    """
    empty = {
        "plate": "",
        "confidence": 0.0,
        "is_valid": False,
        "province": "Unknown",
        "engine": "None",
    }
    if plate_crop is None or plate_crop.size == 0:
        return empty

    started = time.monotonic()
    preprocessed = preprocess_plate_image(plate_crop)
    pytesseract = _tesseract_ready()
    candidates = []

    ocr_images = []
    for view in plate_ocr_views(plate_crop):
        ocr_images.append(view)
        view_prep = preprocess_plate_image(view)
        if view_prep is not None:
            ocr_images.append(view_prep)
            ocr_images.append(cv2.bitwise_not(view_prep))

    if pytesseract:
        for psm in (7, 6):
            for image in ocr_images[:6]:
                if time.monotonic() - started > 7.5:
                    break
                tess_text = _read_with_tesseract(pytesseract, image, psm, 2)
                cleaned_res = clean_and_verify_plate_data(tess_text)
                if not cleaned_res["plate"]:
                    recovered_plate = recover_partial_plate_text(tess_text)
                    if recovered_plate:
                        cleaned_res = clean_and_verify_plate_data(recovered_plate)
                if cleaned_res["plate"] and len(re.sub(r"[^A-Z0-9]", "", cleaned_res["plate"])) >= 3:
                    if plate_candidate_score(cleaned_res["plate"]) >= 90:
                        return {
                            "plate": cleaned_res["plate"],
                            "confidence": 0.93,
                            "is_valid": True,
                            "province": cleaned_res["province"],
                            "engine": "Tesseract OCR",
                        }
                    candidates.append(cleaned_res)

        if refinement_depth == 0 and not candidates and time.monotonic() - started < 6:
            gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if len(plate_crop.shape) == 3 else plate_crop
            _, bright = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY)
            bright_contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if bright_contours:
                bright_contour = max(bright_contours, key=cv2.contourArea)
                bx, by, bw, bh = cv2.boundingRect(bright_contour)
                if bw * bh >= plate_crop.shape[0] * plate_crop.shape[1] * 0.35:
                    bright_crop = plate_crop[by:by + bh, bx:bx + bw]
                    for angle in (-10, 10):
                        height, width = bright_crop.shape[:2]
                        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
                        rotated = cv2.warpAffine(
                            bright_crop, matrix, (width, height), borderMode=cv2.BORDER_REPLICATE
                        )
                        tess_text = _read_with_tesseract(pytesseract, rotated, 7, 2)
                        cleaned_res = clean_and_verify_plate_data(tess_text)
                        if cleaned_res["plate"]:
                            candidates.append(cleaned_res)

        if candidates:
            best_candidate = max(candidates, key=lambda item: plate_candidate_score(item["plate"]))
            return {
                "plate": best_candidate["plate"],
                "confidence": 0.93,
                "is_valid": True,
                "province": best_candidate["province"],
                "engine": "Tesseract OCR",
            }

    if time.monotonic() - started < 6.5:
        reader = get_easyocr_reader()
        if reader is not None:
            try:
                results = reader.readtext(plate_crop)
                if results:
                    results = sorted(results, key=lambda item: item[0][0][0])
                    texts = []
                    confidences = []
                    for _bbox, text, conf in results:
                        sanitized = re.sub(r"[^A-Z0-9.\- ]", "", text.upper()).strip()
                        if sanitized and sanitized not in NOISE_TOKENS and len(sanitized) >= 1:
                            texts.append(sanitized)
                            confidences.append(conf)
                    if texts:
                        full_raw = " ".join(texts)
                        cleaned_res = clean_and_verify_plate_data(full_raw)
                        if cleaned_res["plate"]:
                            avg_conf = sum(confidences) / len(confidences)
                            return {
                                "plate": cleaned_res["plate"],
                                "confidence": round(avg_conf, 2),
                                "is_valid": cleaned_res["is_valid"],
                                "province": cleaned_res["province"],
                                "engine": "EasyOCR / Neural OCR",
                            }
            except Exception:
                pass

    return empty
