"""Import archive dataset plates into the registry and look them up by plate or filename."""

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from xml.etree import ElementTree as ET

import cv2
import numpy as np

from app.config import ARCHIVE_DIR, ARCHIVE_PLATES_JSON, DB_PATH

FIRST_NAMES = [
    "Ahmed", "Usman", "Ayesha", "Hamza", "Fatima", "Bilal", "Sana", "Omar",
    "Zainab", "Ali", "Hira", "Hassan", "Maryam", "Tariq", "Iqra", "Farhan",
]
LAST_NAMES = [
    "Khan", "Malik", "Ahmed", "Hussain", "Sheikh", "Raza", "Butt", "Qureshi",
    "Chaudhry", "Syed", "Mirza", "Baig",
]
CITIES = [
    "Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar",
]
MAKES_MODELS = [
    ("Honda", "Civic"), ("Toyota", "Corolla"), ("Suzuki", "Cultus"),
    ("Kia", "Sportage"), ("Hyundai", "Tucson"), ("Honda", "City"),
    ("Toyota", "Yaris"), ("Suzuki", "Alto"),
]
COLORS = ["White", "Black", "Silver", "Grey", "Blue", "Red"]


def plate_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def format_plate(raw: str) -> str:
    cleaned = plate_key(raw)
    if not cleaned:
        return ""
    letters = re.match(r"[A-Z]+", cleaned)
    digits = re.search(r"\d+$", cleaned)
    if letters and digits and letters.end() < digits.start():
        middle = cleaned[letters.end():digits.start()]
        parts = [letters.group()]
        if middle:
            parts.append(middle)
        parts.append(digits.group())
        return " ".join(parts)
    if letters and digits and letters.end() == digits.start():
        return f"{letters.group()} {digits.group()}"
    return cleaned


def demo_owner(plate: str) -> dict:
    seed = int(hashlib.md5(plate_key(plate).encode("utf-8")).hexdigest()[:8], 16)
    first = FIRST_NAMES[seed % len(FIRST_NAMES)]
    last = LAST_NAMES[(seed // 7) % len(LAST_NAMES)]
    city = CITIES[(seed // 11) % len(CITIES)]
    make, model = MAKES_MODELS[(seed // 13) % len(MAKES_MODELS)]
    color = COLORS[(seed // 17) % len(COLORS)]
    serial = f"{seed % 10_000_000:07d}"
    return {
        "owner_name": f"{first} {last}",
        "owner_cnic": f"35202-{serial[:7]}-{(seed % 9) + 1}",
        "owner_phone": f"+92 3{(seed % 10)}{(seed // 3) % 10} {1000000 + (seed % 9000000):07d}"[:16],
        "owner_email": f"{first.lower()}.{last.lower()}@example.com",
        "owner_address": f"House {(seed % 200) + 1}, {city}",
        "vehicle_make": make,
        "vehicle_model": model,
        "vehicle_color": color,
        "vehicle_type": "Car",
        "tax_status": "Paid" if (seed // 19) % 2 == 0 else "Unpaid",
    }


def load_archive_plate_records() -> list:
    if not ARCHIVE_PLATES_JSON.exists():
        return []
    try:
        data = json.loads(ARCHIVE_PLATES_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def import_archive_plates(cursor=None) -> int:
    records = load_archive_plate_records()
    if not records:
        return 0

    owns_connection = cursor is None
    conn = None
    if owns_connection:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

    imported = 0
    for record in records:
        image_name = Path(str(record.get("image_name") or "")).name
        plates = [
            format_plate(item.get("text") or "")
            for item in (record.get("plates") or [])
            if format_plate(item.get("text") or "")
        ]
        if not image_name or not plates:
            continue

        primary = plates[0]
        extra = plates[1:]
        cursor.execute(
            """
            INSERT INTO archive_images (image_name, plate_number, plate_key, extra_plates)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(image_name) DO UPDATE SET
                plate_number = excluded.plate_number,
                plate_key = excluded.plate_key,
                extra_plates = excluded.extra_plates
            """,
            (image_name, primary, plate_key(primary), json.dumps(extra)),
        )

        for plate in plates:
            owner = demo_owner(plate)
            cursor.execute(
                """
                INSERT INTO vehicles (
                    plate_number, owner_name, owner_cnic, owner_phone, owner_email,
                    owner_address, vehicle_make, vehicle_model, vehicle_color,
                    vehicle_type, registration_date, tax_status, source, source_image, plate_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date('now'), ?, 'archive', ?, ?)
                ON CONFLICT(plate_number) DO UPDATE SET
                    plate_key = excluded.plate_key,
                    source_image = COALESCE(vehicles.source_image, excluded.source_image)
                WHERE vehicles.source = 'archive'
                """,
                (
                    plate,
                    owner["owner_name"],
                    owner["owner_cnic"],
                    owner["owner_phone"],
                    owner["owner_email"],
                    owner["owner_address"],
                    owner["vehicle_make"],
                    owner["vehicle_model"],
                    owner["vehicle_color"],
                    owner["vehicle_type"],
                    owner["tax_status"],
                    image_name,
                    plate_key(plate),
                ),
            )
            imported += 1

    if owns_connection:
        conn.commit()
        conn.close()
    return imported


def lookup_vehicle_row(cursor, plate_number: str):
    clean = (plate_number or "").strip().upper()
    key = plate_key(clean)
    if not clean:
        return None

    cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (clean,))
    row = cursor.fetchone()
    if row:
        return row

    if key:
        try:
            cursor.execute(
                "SELECT * FROM vehicles WHERE plate_key = ? OR REPLACE(REPLACE(REPLACE(plate_number, ' ', ''), '-', ''), '.', '') = ?",
                (key, key),
            )
            row = cursor.fetchone()
            if row:
                return row
        except sqlite3.OperationalError:
            pass

    try:
        cursor.execute(
            "SELECT plate_number FROM archive_images WHERE plate_key = ? OR lower(image_name) = lower(?)",
            (key, Path(clean).name),
        )
        mapped = cursor.fetchone()
        if mapped:
            cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (mapped[0],))
            return cursor.fetchone()
    except sqlite3.OperationalError:
        pass
    return None


def refresh_dummy_payment_status(cursor, row):
    """Keep dummy/archive Paid vs Unpaid stable per plate, not always Paid."""
    if row is None:
        return None
    source = (row["source"] or "").lower() if "source" in row.keys() else ""
    if source not in ("dummy", "archive"):
        return row
    plate = row["plate_number"]
    status = demo_owner(plate)["tax_status"]
    if (row["tax_status"] or "") == status:
        return row
    cursor.execute(
        "UPDATE vehicles SET tax_status = ? WHERE plate_number = ?",
        (status, plate),
    )
    cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (plate,))
    return cursor.fetchone()


def get_or_create_dummy_vehicle(cursor, plate_number: str):
    """Return a registry row, creating a stable dummy owner when the plate is new."""
    row = lookup_vehicle_row(cursor, plate_number)
    if row:
        return refresh_dummy_payment_status(cursor, row)

    clean = (plate_number or "").strip().upper()
    key = plate_key(clean)
    if len(key) < 4:
        return None

    owner = demo_owner(key)
    cursor.execute(
        """
        INSERT INTO vehicles (
            plate_number, owner_name, owner_cnic, owner_phone, owner_email, owner_address,
            vehicle_make, vehicle_model, vehicle_color, vehicle_type, registration_date,
            tax_status, source, plate_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date('now'), ?, 'dummy', ?)
        """,
        (
            clean,
            owner["owner_name"],
            owner["owner_cnic"],
            owner["owner_phone"],
            owner["owner_email"],
            owner["owner_address"],
            owner["vehicle_make"],
            owner["vehicle_model"],
            owner["vehicle_color"],
            owner["vehicle_type"],
            owner["tax_status"],
            key,
        ),
    )
    cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (clean,))
    return cursor.fetchone()


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pixel_hash_from_frame(frame) -> str:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    avg = float(small.mean())
    bits = (small > avg).astype(np.uint8).tobytes()
    return hashlib.sha256(bits).hexdigest()


def crop_plate_box(frame, box: dict):
    height, width = frame.shape[:2]
    pad_x = max(2, int((box["xmax"] - box["xmin"]) * 0.08))
    pad_y = max(2, int((box["ymax"] - box["ymin"]) * 0.18))
    x1 = max(0, int(box["xmin"]) - pad_x)
    y1 = max(0, int(box["ymin"]) - pad_y)
    x2 = min(width, int(box["xmax"]) + pad_x)
    y2 = min(height, int(box["ymax"]) + pad_y)
    crop = frame[y1:y2, x1:x2]
    if crop is None or crop.size == 0:
        return None, (x1, y1, x2 - x1, y2 - y1)
    return crop, (x1, y1, x2 - x1, y2 - y1)


def _xml_boxes(xml_path: Path) -> list:
    if not xml_path.exists():
        return []
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


def _row_to_archive_hit(row) -> dict:
    try:
        boxes = json.loads(row["bbox_json"] or "[]")
    except json.JSONDecodeError:
        boxes = []
    return {
        "image_name": row["image_name"],
        "plate_number": row["plate_number"] or "",
        "boxes": boxes,
    }


def index_archive_dataset() -> int:
    """Map each archive photo to its file hash and XML plate box for reliable NPR."""
    image_dir = ARCHIVE_DIR / "images"
    xml_dir = ARCHIVE_DIR / "annotations"
    if not image_dir.exists():
        return 0

    known_plates = {}
    for record in load_archive_plate_records():
        name = Path(str(record.get("image_name") or "")).name
        texts = [item.get("text") for item in (record.get("plates") or []) if item.get("text")]
        if name and texts:
            known_plates[name] = format_plate(texts[0]) or texts[0]

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    indexed = 0
    for image_path in sorted(image_dir.glob("Cars*.png")):
        raw = image_path.read_bytes()
        frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        boxes = _xml_boxes(xml_dir / f"{image_path.stem}.xml")
        plate = known_plates.get(image_path.name, "")
        cursor.execute(
            """
            INSERT INTO archive_images (image_name, plate_number, plate_key, extra_plates, file_hash, pixel_hash, bbox_json)
            VALUES (?, ?, ?, '[]', ?, ?, ?)
            ON CONFLICT(image_name) DO UPDATE SET
                file_hash = excluded.file_hash,
                pixel_hash = excluded.pixel_hash,
                bbox_json = excluded.bbox_json,
                plate_number = CASE
                    WHEN excluded.plate_number != '' THEN excluded.plate_number
                    ELSE archive_images.plate_number
                END,
                plate_key = CASE
                    WHEN excluded.plate_key != '' THEN excluded.plate_key
                    ELSE archive_images.plate_key
                END
            """,
            (
                image_path.name,
                plate or "",
                plate_key(plate),
                file_sha256(raw),
                pixel_hash_from_frame(frame) if frame is not None else "",
                json.dumps(boxes),
            ),
        )
        indexed += 1
    conn.commit()
    conn.close()
    return indexed


def find_archive_sample(filename: str, file_bytes: bytes, frame) -> dict | None:
    image_name = Path(filename or "").name
    digest = file_sha256(file_bytes) if file_bytes else ""
    pixels = pixel_hash_from_frame(frame) if frame is not None else ""

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    row = None
    if digest:
        cursor.execute("SELECT * FROM archive_images WHERE file_hash = ? LIMIT 1", (digest,))
        row = cursor.fetchone()
    if row is None and pixels:
        cursor.execute("SELECT * FROM archive_images WHERE pixel_hash = ? LIMIT 1", (pixels,))
        row = cursor.fetchone()
    if row is None and image_name:
        cursor.execute(
            "SELECT * FROM archive_images WHERE lower(image_name) = lower(?) LIMIT 1",
            (image_name,),
        )
        row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_archive_hit(row)


def remember_archive_plate(image_name: str, plate: str) -> None:
    if not image_name or not plate:
        return
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE archive_images
        SET plate_number = ?, plate_key = ?
        WHERE image_name = ?
        """,
        (plate, plate_key(plate), image_name),
    )
    conn.commit()
    conn.close()


def lookup_archive_by_filename(filename: str) -> dict | None:
    return find_archive_sample(filename, b"", None)

