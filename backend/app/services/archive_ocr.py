"""One-time OCR of archive dataset plates using XML bounding boxes."""

import json
import os
import re
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

import cv2
import pytesseract

from app.config import ARCHIVE_DIR, ARCHIVE_PLATES_JSON
from app.services.archive_registry import format_plate, plate_key


def _configure_tesseract() -> bool:
    tesseract_paths = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    )
    installed = next((path for path in tesseract_paths if os.path.isfile(path)), None)
    if installed:
        pytesseract.pytesseract.tesseract_cmd = installed
        return True
    return bool(shutil.which("tesseract"))


def _read_boxes(xml_path: Path) -> list[dict]:
    root = ET.parse(xml_path).getroot()
    boxes = []
    for obj in root.findall("object"):
        box = obj.find("bndbox")
        if box is None:
            continue
        boxes.append({
            "xmin": int(float(box.findtext("xmin"))),
            "ymin": int(float(box.findtext("ymin"))),
            "xmax": int(float(box.findtext("xmax"))),
            "ymax": int(float(box.findtext("ymax"))),
        })
    return boxes


def _crop_plate(image, box: dict):
    height, width = image.shape[:2]
    pad_x = max(2, int((box["xmax"] - box["xmin"]) * 0.08))
    pad_y = max(2, int((box["ymax"] - box["ymin"]) * 0.18))
    x1 = max(0, box["xmin"] - pad_x)
    y1 = max(0, box["ymin"] - pad_y)
    x2 = min(width, box["xmax"] + pad_x)
    y2 = min(height, box["ymax"] + pad_y)
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    crop_h, crop_w = crop.shape[:2]
    if crop_h < 70:
        scale = 70.0 / max(crop_h, 1)
        crop = cv2.resize(crop, (max(1, int(crop_w * scale)), 70), interpolation=cv2.INTER_CUBIC)
    return crop


_easyocr_reader = None


def _easyocr_crop(crop) -> str:
    global _easyocr_reader
    try:
        import easyocr
    except Exception:
        return ""
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    try:
        results = _easyocr_reader.readtext(crop)
    except Exception:
        return ""
    texts = []
    for _bbox, text, _conf in results:
        formatted = format_plate(text)
        if formatted:
            texts.append(formatted)
    if not texts:
        return ""
    return max(texts, key=lambda item: len(plate_key(item)))


def _ocr_crop(crop) -> str:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    candidates = []
    for image in (crop, gray, thresh):
        for psm in (7, 6, 8):
            config = f"--oem 3 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            try:
                raw = pytesseract.image_to_string(image, config=config, timeout=4)
            except Exception:
                continue
            text = format_plate(raw)
            if len(plate_key(text)) >= 3:
                candidates.append(text)

    def score(text: str) -> int:
        key = plate_key(text)
        value = len(key)
        if 4 <= len(key) <= 12:
            value += 10
        if re.search(r"[A-Z]", key) and re.search(r"\d", key):
            value += 15
        if len(key) < 3 or len(key) > 14:
            value -= 20
        return value

    best = max(candidates, key=score) if candidates else ""
    if not best or score(best) < 12:
        easy = _easyocr_crop(crop)
        if easy and (not best or score(easy) > score(best)):
            best = easy
    return best if best and len(plate_key(best)) >= 3 else ""


def ocr_archive_dataset(limit: int | None = None) -> Path:
    if not _configure_tesseract():
        raise RuntimeError("Tesseract OCR is not installed or not on PATH.")

    image_dir = ARCHIVE_DIR / "images"
    xml_dir = ARCHIVE_DIR / "annotations"
    existing = {}
    if ARCHIVE_PLATES_JSON.exists():
        try:
            for row in json.loads(ARCHIVE_PLATES_JSON.read_text(encoding="utf-8")):
                existing[row["image_name"]] = row
        except (OSError, json.JSONDecodeError, KeyError):
            existing = {}

    xml_files = sorted(xml_dir.glob("Cars*.xml"), key=lambda path: path.stem)
    if limit:
        xml_files = xml_files[:limit]

    results = []
    for index, xml_path in enumerate(xml_files, start=1):
        image_name = f"{xml_path.stem}.png"
        if image_name in existing and existing[image_name].get("plates"):
            results.append(existing[image_name])
            continue

        image_path = image_dir / image_name
        image = cv2.imread(str(image_path))
        plates = []
        if image is not None:
            for box in _read_boxes(xml_path):
                crop = _crop_plate(image, box)
                if crop is None:
                    continue
                text = _ocr_crop(crop)
                if text:
                    plates.append({"text": text, **box})

        row = {"image_name": image_name, "plates": plates}
        results.append(row)
        existing[image_name] = row

        if index % 10 == 0 or index == len(xml_files):
            ARCHIVE_PLATES_JSON.write_text(json.dumps(list(existing.values()), indent=2), encoding="utf-8")
            print(f"[Archive OCR] {index}/{len(xml_files)} images, {sum(1 for item in existing.values() if item.get('plates'))} with text")

    ARCHIVE_PLATES_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return ARCHIVE_PLATES_JSON


if __name__ == "__main__":
    path = ocr_archive_dataset()
    print(f"[Archive OCR] Wrote {path}")
