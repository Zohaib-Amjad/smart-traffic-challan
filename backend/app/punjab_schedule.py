"""Punjab Traffic Police challan schedule (Twelfth Schedule, PMVO 1965).

Fines are not one national amount. This module stores Punjab's published
columns so a motorcycle and an HTV are not charged the same.
"""

from typing import Optional

PROVINCE = "Punjab"
LAW_REFERENCE = "Twelfth Schedule, Provincial Motor Vehicles Ordinance, 1965"
DUE_DAYS_DEFAULT = 15
EFFECTIVE_FROM = "2025-01-01"

FINE_BRACKETS = (
    {"code": "motorcycle", "label": "Motorcycle"},
    {"code": "three_wheeler", "label": "Three-wheeler"},
    {"code": "car_under_2000cc", "label": "Motorcar/Jeep under 2000cc"},
    {"code": "car_over_2000cc", "label": "Motorcar/Jeep over 2000cc"},
    {"code": "psv_htv", "label": "PSV / Carrier / HTV / Tractor / Trailer"},
)

VEHICLE_TYPES = (
    {"code": "Motorcycle", "name": "Motorcycle", "category": "Two-wheelers", "fine_bracket": "motorcycle", "sort_order": 1},
    {"code": "Scooter", "name": "Scooter", "category": "Two-wheelers", "fine_bracket": "motorcycle", "sort_order": 2},
    {"code": "Electric motorcycle/scooter", "name": "Electric motorcycle/scooter", "category": "Two-wheelers", "fine_bracket": "motorcycle", "sort_order": 3},
    {"code": "Rickshaw", "name": "Rickshaw", "category": "Three-wheelers", "fine_bracket": "three_wheeler", "sort_order": 10},
    {"code": "Qingqi / three-wheeler", "name": "Qingqi / three-wheeler", "category": "Three-wheelers", "fine_bracket": "three_wheeler", "sort_order": 11},
    {"code": "Other three-wheel vehicle", "name": "Other three-wheel vehicle", "category": "Three-wheelers", "fine_bracket": "three_wheeler", "sort_order": 12},
    {"code": "Motor car", "name": "Motor car", "category": "Light vehicles", "fine_bracket": "car", "sort_order": 20},
    {"code": "Jeep", "name": "Jeep", "category": "Light vehicles", "fine_bracket": "car", "sort_order": 21},
    {"code": "SUV", "name": "SUV", "category": "Light vehicles", "fine_bracket": "car", "sort_order": 22},
    {"code": "Motor cab", "name": "Motor cab", "category": "Light vehicles", "fine_bracket": "car", "sort_order": 23},
    {"code": "Private vehicle", "name": "Private vehicle", "category": "Light vehicles", "fine_bracket": "car", "sort_order": 24},
    {"code": "Delivery van", "name": "Delivery van", "category": "Light transport", "fine_bracket": "psv_htv", "sort_order": 30},
    {"code": "Pickup", "name": "Pickup", "category": "Light transport", "fine_bracket": "psv_htv", "sort_order": 31},
    {"code": "LTV", "name": "LTV", "category": "Light transport", "fine_bracket": "psv_htv", "sort_order": 32},
    {"code": "Small passenger van", "name": "Small passenger van", "category": "Light transport", "fine_bracket": "psv_htv", "sort_order": 33},
    {"code": "Bus", "name": "Bus", "category": "Public-service vehicles", "fine_bracket": "psv_htv", "sort_order": 40},
    {"code": "Coaster", "name": "Coaster", "category": "Public-service vehicles", "fine_bracket": "psv_htv", "sort_order": 41},
    {"code": "Taxi/cab", "name": "Taxi/cab", "category": "Public-service vehicles", "fine_bracket": "psv_htv", "sort_order": 42},
    {"code": "Stage carriage", "name": "Stage carriage", "category": "Public-service vehicles", "fine_bracket": "psv_htv", "sort_order": 43},
    {"code": "Contract carriage", "name": "Contract carriage", "category": "Public-service vehicles", "fine_bracket": "psv_htv", "sort_order": 44},
    {"code": "Truck", "name": "Truck", "category": "Heavy transport", "fine_bracket": "psv_htv", "sort_order": 50},
    {"code": "Trailer", "name": "Trailer", "category": "Heavy transport", "fine_bracket": "psv_htv", "sort_order": 51},
    {"code": "HTV", "name": "Heavy Transport Vehicle (HTV)", "category": "Heavy transport", "fine_bracket": "psv_htv", "sort_order": 52},
    {"code": "Goods carrier", "name": "Goods carrier", "category": "Heavy transport", "fine_bracket": "psv_htv", "sort_order": 53},
    {"code": "Tractor", "name": "Tractor", "category": "Special vehicles", "fine_bracket": "psv_htv", "sort_order": 60},
    {"code": "Road roller", "name": "Road roller", "category": "Special vehicles", "fine_bracket": "psv_htv", "sort_order": 61},
    {"code": "Other specified motor vehicle", "name": "Other specified motor vehicle", "category": "Special vehicles", "fine_bracket": "psv_htv", "sort_order": 62},
)

VEHICLE_TYPE_ALIASES = {
    "car": "Motor car",
    "car / sedan": "Motor car",
    "sedan": "Motor car",
    "hatchback": "Motor car",
    "suv / jeep": "SUV",
    "motorcycle / bike": "Motorcycle",
    "bike": "Motorcycle",
    "truck / pickup": "Truck",
    "bus / van": "Bus",
    "other": "Private vehicle",
    "qingqi": "Qingqi / three-wheeler",
    "three-wheeler": "Qingqi / three-wheeler",
    "three wheeler": "Qingqi / three-wheeler",
}

VIOLATIONS = (
    {"code": "V-01", "title": "Exceeding prescribed speed limit", "category": "Speed", "sort_order": 1},
    {"code": "V-02", "title": "Carrying passengers beyond permissible limit", "category": "Loading", "sort_order": 2},
    {"code": "V-03", "title": "Violation of traffic signals (electronic/manual)", "category": "Signals", "sort_order": 3},
    {"code": "V-04", "title": "Overloading a goods vehicle", "category": "Loading", "sort_order": 4},
    {"code": "V-05", "title": "Driving at night without proper lights", "category": "Equipment", "sort_order": 5},
    {"code": "V-06", "title": "Driving on the wrong side of the road", "category": "Movement", "sort_order": 6},
    {"code": "V-07", "title": "Driving with tinted/covered glasses", "category": "Equipment", "sort_order": 7},
    {"code": "V-08", "title": "Violation of line/lane/zebra crossing", "category": "Movement", "sort_order": 8},
    {"code": "V-09", "title": "Plying a motor vehicle where and when prohibited", "category": "Movement", "sort_order": 9},
    {"code": "V-10", "title": "Obstructing traffic", "category": "Movement", "sort_order": 10},
    {"code": "V-11", "title": "Reckless and negligent driving", "category": "Conduct", "sort_order": 11},
    {"code": "V-12", "title": "Driving without a valid driving licence", "category": "Documents", "sort_order": 12},
    {"code": "V-13", "title": "Pressure/musical horn or horn in a silence zone", "category": "Equipment", "sort_order": 13},
    {"code": "V-14", "title": "Emitting excessive smoke", "category": "Environment", "sort_order": 14},
    {"code": "V-15", "title": "Driving an unregistered motor vehicle", "category": "Documents", "sort_order": 15},
    {"code": "V-16", "title": "Driving in violation of age restrictions", "category": "Documents", "sort_order": 16},
    {"code": "V-17", "title": "Driving without a fitness certificate", "category": "Documents", "sort_order": 17},
    {"code": "V-18", "title": "Driving without/against route permit conditions", "category": "Documents", "sort_order": 18},
    {"code": "V-19", "title": "Motorcycle without crash helmet", "category": "Safety", "sort_order": 19},
    {"code": "V-20", "title": "Pillion riding by more than two persons", "category": "Safety", "sort_order": 20},
    {"code": "V-21", "title": "Using handheld mobile phone while driving", "category": "Conduct", "sort_order": 21},
    {"code": "V-22", "title": "Driving without seat belt on a notified road", "category": "Safety", "sort_order": 22},
    {"code": "V-23", "title": "Violation of parking rules", "category": "Parking", "sort_order": 23},
    {"code": "V-24", "title": "Illegal/tinted number plate or non-display of official plate", "category": "Registration", "sort_order": 24},
    {"code": "V-25", "title": "Violation of other Motor Vehicles Ordinance/rules (s.112)", "category": "Other", "sort_order": 25},
)

# Columns: motorcycle, three_wheeler, car_under_2000cc, car_over_2000cc, psv_htv. None = not applicable.
FINE_MATRIX = {
    "V-01": (2000, 3000, 5000, 20000, 20000),
    "V-02": (None, 3000, 5000, 10000, 15000),
    "V-03": (2000, 3000, 5000, 10000, 15000),
    "V-04": (None, 3000, 5000, 10000, 15000),
    "V-05": (2000, 3000, 3000, 8000, 10000),
    "V-06": (2000, 3000, 5000, 10000, 15000),
    "V-07": (None, None, 5000, 10000, 10000),
    "V-08": (2000, 3000, 3000, 8000, 15000),
    "V-09": (2000, 3000, 3000, 8000, 15000),
    "V-10": (2000, 3000, 5000, 10000, 15000),
    "V-11": (3000, 3000, 5000, 10000, 15000),
    "V-12": (2000, 3000, 5000, 10000, 15000),
    "V-13": (2000, 2000, 2000, 5000, 10000),
    "V-14": (2000, 3000, 3000, 8000, 15000),
    "V-15": (2000, 3000, 5000, 10000, 15000),
    "V-16": (2000, 3000, 5000, 10000, 15000),
    "V-17": (2000, 3000, None, 10000, 15000),
    "V-18": (None, 3000, None, None, 15000),
    "V-19": (2000, 2000, None, None, None),
    "V-20": (2000, None, None, None, None),
    "V-21": (2000, 3000, 5000, 10000, 15000),
    "V-22": (None, None, 5000, 10000, 10000),
    "V-23": (2000, 3000, 5000, 10000, 15000),
    "V-24": (2000, 3000, 5000, 10000, 15000),
    "V-25": (2000, 3000, 3000, 8000, 10000),
}

BRACKET_INDEX = {
    "motorcycle": 0,
    "three_wheeler": 1,
    "car_under_2000cc": 2,
    "car_over_2000cc": 3,
    "psv_htv": 4,
}

_VEHICLE_TYPE_BY_CODE = {item["code"].lower(): item for item in VEHICLE_TYPES}
_VIOLATION_BY_CODE = {item["code"]: item for item in VIOLATIONS}
_VIOLATION_BY_TITLE = {item["title"].lower(): item for item in VIOLATIONS}

LEGACY_VIOLATION_MAP = {
    "v-red-light": "V-03",
    "v-signal": "V-03",
    "v-overspeed": "V-01",
    "v-wrong-way": "V-06",
    "v-wrong-parking": "V-23",
    "v-no-helmet": "V-19",
    "v-triple-riding": "V-20",
    "v-lane-violation": "V-08",
    "v-phone-usage": "V-21",
    "v-tinted-glass": "V-07",
    "v-manual": "V-25",
}


def normalize_vehicle_type(vehicle_type: Optional[str]) -> str:
    raw = (vehicle_type or "").strip()
    if not raw:
        return "Motor car"
    alias = VEHICLE_TYPE_ALIASES.get(raw.lower())
    if alias:
        return alias
    match = _VEHICLE_TYPE_BY_CODE.get(raw.lower())
    if match:
        return match["code"]
    return raw


def resolve_fine_bracket(vehicle_type: Optional[str], engine_cc: Optional[int] = None) -> str:
    """Map a registered vehicle onto one of Punjab's five fine columns."""
    code = normalize_vehicle_type(vehicle_type)
    spec = _VEHICLE_TYPE_BY_CODE.get(code.lower())
    family = spec["fine_bracket"] if spec else "car"
    if family != "car":
        return family
    try:
        cc_value = int(engine_cc) if engine_cc not in (None, "") else 1600
    except (TypeError, ValueError):
        cc_value = 1600
    if cc_value > 2000:
        return "car_over_2000cc"
    return "car_under_2000cc"


def resolve_violation_code(code_or_title: Optional[str]) -> Optional[str]:
    raw = (code_or_title or "").strip()
    if not raw:
        return None
    head = raw.split(" - Rs")[0].split(" - PKR")[0].strip()
    upper = head.upper()
    if upper in _VIOLATION_BY_CODE:
        return upper
    mapped = LEGACY_VIOLATION_MAP.get(upper.lower())
    if mapped:
        return mapped
    title_hit = _VIOLATION_BY_TITLE.get(head.lower())
    if title_hit:
        return title_hit["code"]
    lowered = head.lower()
    if "speed" in lowered:
        return "V-01"
    if "signal" in lowered or "red light" in lowered:
        return "V-03"
    if "helmet" in lowered:
        return "V-19"
    if "phone" in lowered or "mobile" in lowered:
        return "V-21"
    if "park" in lowered:
        return "V-23"
    if "wrong" in lowered or "one-way" in lowered:
        return "V-06"
    if "pillion" in lowered or "triple" in lowered:
        return "V-20"
    if "seat" in lowered:
        return "V-22"
    if "tinted" in lowered:
        return "V-07"
    if "plate" in lowered:
        return "V-24"
    if "zebra" in lowered or "lane" in lowered:
        return "V-08"
    return None


def lookup_fine(violation_code: str, vehicle_type: Optional[str] = None, engine_cc: Optional[int] = None) -> dict:
    """Return the Punjab amount for this offence and vehicle, or mark it not applicable."""
    code = resolve_violation_code(violation_code) or ""
    violation = _VIOLATION_BY_CODE.get(code)
    bracket = resolve_fine_bracket(vehicle_type, engine_cc)
    amount = None
    if violation and code in FINE_MATRIX:
        amount = FINE_MATRIX[code][BRACKET_INDEX[bracket]]
    return {
        "province": PROVINCE,
        "law_reference": LAW_REFERENCE,
        "violation_code": code,
        "violation_name": violation["title"] if violation else "",
        "vehicle_type": normalize_vehicle_type(vehicle_type),
        "fine_bracket": bracket,
        "fine_bracket_label": next(item["label"] for item in FINE_BRACKETS if item["code"] == bracket),
        "amount": amount,
        "applicable": amount is not None,
    }


def schedule_for_vehicle(vehicle_type: Optional[str] = None, engine_cc: Optional[int] = None) -> dict:
    bracket = resolve_fine_bracket(vehicle_type, engine_cc)
    violations = []
    for item in VIOLATIONS:
        amount = FINE_MATRIX[item["code"]][BRACKET_INDEX[bracket]]
        violations.append({
            "code": item["code"],
            "title": item["title"],
            "category": item["category"],
            "law_reference": LAW_REFERENCE,
            "amount": amount,
            "applicable": amount is not None,
        })
    return {
        "province": PROVINCE,
        "law_reference": LAW_REFERENCE,
        "due_days_default": DUE_DAYS_DEFAULT,
        "vehicle_type": normalize_vehicle_type(vehicle_type),
        "fine_bracket": bracket,
        "fine_bracket_label": next(item["label"] for item in FINE_BRACKETS if item["code"] == bracket),
        "violations": violations,
        "vehicle_types": list(VEHICLE_TYPES),
        "fine_brackets": list(FINE_BRACKETS),
    }


def grouped_vehicle_types() -> list:
    groups = []
    current = None
    for item in VEHICLE_TYPES:
        entry = {**item, "requires_engine_cc": item["fine_bracket"] == "car"}
        if current is None or current["category"] != item["category"]:
            current = {"category": item["category"], "types": []}
            groups.append(current)
        current["types"].append(entry)
    return groups


def seed_punjab_schedule(cursor):
    """Write Punjab vehicle types, 25 offences, and the 5-column fine matrix."""
    cursor.execute("DELETE FROM vehicle_types")
    cursor.execute("DELETE FROM violations")
    cursor.execute("DELETE FROM fines")
    cursor.execute("DELETE FROM violation_tariffs")
    for item in VEHICLE_TYPES:
        cursor.execute(
            """
            INSERT INTO vehicle_types (code, name, category, fine_bracket, sort_order, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (item["code"], item["name"], item["category"], item["fine_bracket"], item["sort_order"]),
        )
    for item in VIOLATIONS:
        cursor.execute(
            """
            INSERT INTO violations (code, title, category, law_reference, sort_order, active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (item["code"], item["title"], item["category"], LAW_REFERENCE, item["sort_order"]),
        )
        amounts = FINE_MATRIX[item["code"]]
        for bracket, amount in zip(BRACKET_INDEX.keys(), amounts):
            cursor.execute(
                """
                INSERT INTO fines (violation_code, fine_bracket, amount, province, law_reference, effective_from)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item["code"], bracket, amount, PROVINCE, LAW_REFERENCE, EFFECTIVE_FROM),
            )
        display_amount = next((value for value in amounts if value is not None), 0)
        cursor.execute(
            """
            INSERT INTO violation_tariffs (code, title, description, fine_amount, points)
            VALUES (?, ?, ?, ?, 2)
            """,
            (item["code"], item["title"], LAW_REFERENCE, display_amount),
        )
