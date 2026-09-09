"""Build printable challan PDFs in a Pakistani citation layout."""

import os
import sqlite3
import datetime
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

from app.config import DB_PATH, EVIDENCE_DIR, PDFS_DIR, STATIC_DIR, HOTLINE, POLICE_DEPT_NAME


LINE = colors.HexColor("#111111")
MUTED = colors.HexColor("#374151")
HEAD_BG = colors.HexColor("#E5E7EB")
FOOT_BG = colors.HexColor("#9F1239")
LOGO_PATH = os.path.join(str(STATIC_DIR), "logo.png")


def generate_qr_code(challan_no: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(f"http://127.0.0.1:8000/challan/{challan_no}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#111111", back_color="white")
    qr_path = os.path.join(PDFS_DIR, f"{challan_no}_qr.png")
    qr_img.save(qr_path)
    return qr_path


def _dash(value) -> str:
    text = "" if value is None else str(value).strip()
    return text if text else "—"


def _money(amount) -> str:
    try:
        return f"Rs. {int(amount):,}/-"
    except (TypeError, ValueError):
        return "—"


def _parse_dt(value):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text[:19] if " " in text else text[:10], fmt)
        except ValueError:
            continue
    return None


def _short_date(value) -> str:
    parsed = value if isinstance(value, datetime.datetime) else _parse_dt(value)
    if not parsed:
        return _dash(value)
    return parsed.strftime("%d-%b-%Y")


def _p(text, style):
    return Paragraph(str(text), style)


def _draw_watermark(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFillColor(colors.Color(0.55, 0.55, 0.62, alpha=0.12))
    canvas_obj.setFont("Helvetica-Bold", 22)
    canvas_obj.translate(A4[0] / 2, A4[1] / 2)
    canvas_obj.rotate(28)
    canvas_obj.drawCentredString(0, 0, "SMART TRAFFIC CHALLAN SYSTEM")
    canvas_obj.restoreState()
    canvas_obj.saveState()
    canvas_obj.setFillColor(FOOT_BG)
    canvas_obj.rect(0, 0, A4[0], 14 * mm, fill=1, stroke=0)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 8)
    canvas_obj.drawCentredString(
        A4[0] / 2,
        6 * mm,
        "This challan can be paid at the issuing office. Mark as Paid in this system is a simulation.",
    )
    canvas_obj.restoreState()


def generate_challan_pdf(challan_no: str) -> str:
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM challans WHERE challan_no = ?", (challan_no,))
    ch = cursor.fetchone()
    if not ch:
        conn.close()
        return ""
    cursor.execute("SELECT * FROM vehicles WHERE plate_number = ?", (ch["plate_number"],))
    veh = cursor.fetchone()
    conn.close()

    pdf_filename = f"{challan_no}.pdf"
    pdf_filepath = os.path.join(PDFS_DIR, pdf_filename)

    styles = getSampleStyleSheet()
    small = ParagraphStyle("PkSmall", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=MUTED)
    bold = ParagraphStyle("PkBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=LINE)
    title = ParagraphStyle("PkTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=1, textColor=LINE)
    kicker = ParagraphStyle("PkKicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=11, alignment=1, textColor=LINE)
    cell = ParagraphStyle("PkCell", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=LINE)
    lab = ParagraphStyle("PkLab", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=LINE)
    legal = ParagraphStyle("PkLegal", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=LINE)

    issued = _parse_dt(ch["created_at"]) or datetime.datetime.now()
    due = _parse_dt(ch["due_date"])
    amount = ch["fine_amount"] or 0
    source = ((veh["source"] if veh else "") or "").lower()
    registry_known = source in ("user", "demo")
    make = _dash(veh["vehicle_make"] if veh and registry_known else "")
    color = _dash(veh["vehicle_color"] if veh and registry_known else "")
    owner = _dash(veh["owner_name"] if veh else "")
    cnic = _dash(veh["owner_cnic"] if veh else "")
    address = _dash(veh["owner_address"] if veh else "")
    reg_year = _dash((veh["registration_date"][:4] if veh and veh["registration_date"] else ""))

    qr_path = generate_qr_code(challan_no)
    logo = Image(LOGO_PATH, width=18 * mm, height=18 * mm) if os.path.exists(LOGO_PATH) else _p("", small)
    qr_img = Image(qr_path, width=32 * mm, height=32 * mm)

    header = Table(
        [[
            "",
            [_p("Electronic Traffic Violation Notice", kicker), _p("Smart Traffic Challan System", title)],
            logo,
        ]],
        colWidths=[22 * mm, 146 * mm, 22 * mm],
    )
    header.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    kv_html = (
        f"<b>Notice No:</b> {_dash(ch['challan_no'])}<br/>"
        f"<b>Number Plate:</b> {_dash(ch['plate_number'])}<br/>"
        f"<b>Amount:</b> {_money(amount)}<br/>"
        f"<b>Black Points:</b> —<br/>"
        f"<b>Issued Date:</b> {_short_date(issued)}<br/>"
        f"<b>Due Date:</b> {_short_date(due)}"
    )
    paid = Table(
        [
            [_p("<b>Paid By</b>", bold), "", ""],
            [_p("", lab), _p("<b>Date</b>", lab), _p("<b>Amount</b>", lab)],
            [_p("Discounted", cell), _p(_short_date(issued + datetime.timedelta(days=14)), cell), _p(_money(round(amount / 2)), cell)],
            [_p("Standard", cell), _p(_short_date(due), cell), _p(_money(amount), cell)],
            [_p("Penalty", cell), _p("After due date", cell), _p(_money(amount * 2), cell)],
        ],
        colWidths=[28 * mm, 32 * mm, 28 * mm],
    )
    paid.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 1), HEAD_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    qr_block = Table(
        [
            [_p("<b>Smart Traffic Challan System</b><br/>Punjab, Pakistan", bold)],
            [qr_img],
            [_p("Please scan QR Code to view details.", small)],
        ],
        colWidths=[48 * mm],
    )
    qr_block.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    notice = Table(
        [[qr_block, _p(kv_html, cell), paid]],
        colWidths=[50 * mm, 62 * mm, 88 * mm],
    )
    notice.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    details_inner = Table(
        [
            [
                _p("<b>Date &amp; Time Of Offence</b><br/>" + _dash(ch["created_at"]), cell),
                _p("<b>Place Of Violation</b><br/>" + _dash(ch["location"]), cell),
                _p("<b>Violation Type</b><br/>" + _dash(ch["violation_name"]), cell),
                _p("<b>Amount</b><br/>" + _money(amount), cell),
            ],
            [
                _p("<b>Name</b><br/>" + owner, cell),
                "",
                _p("<b>CNIC</b><br/>" + cnic, cell),
                _p("<b>License</b><br/>—", cell),
            ],
            [
                _p("<b>Address</b><br/>" + address, cell),
                "",
                "",
                "",
            ],
            [
                _p("<b>Veh Reg Year</b><br/>" + reg_year, cell),
                _p("<b>Make</b><br/>" + make, cell),
                _p("<b>Color</b><br/>" + color, cell),
                _p("<b>Chassis No / Engine No</b><br/>—", cell),
            ],
        ],
        colWidths=[50 * mm, 50 * mm, 50 * mm, 50 * mm],
    )
    details_inner.setStyle(TableStyle([
        ("SPAN", (0, 1), (1, 1)),
        ("SPAN", (0, 2), (-1, 2)),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    details = Table(
        [[_p("Violation / Vehicle Details", bold)], [details_inner]],
        colWidths=[200 * mm],
    )
    details.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("TOPPADDING", (0, 0), (-1, 0), 4),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    legal_text = f"""
    The images of the above-mentioned vehicle were captured, reviewed, and confirmed as a traffic
    violation under the Twelfth Schedule, Provincial Motor Vehicles Ordinance, 1965.<br/><br/>
    <b>INSTRUCTIONS:</b> Pay this notice by the due date shown above. This is a demonstration e-challan
    for the Smart Traffic Challan System (FYP). Payment in this app is recorded with Mark as Paid (simulate).<br/><br/>
    <b>VERIFICATION PROCESS:</b> For queries use helpline {HOTLINE}. Scan the QR code to open this ticket.<br/><br/>
    <b>TERMS &amp; CONDITIONS:</b> Discounted amount if paid within 14 days of issue. Standard amount if paid
    by the due date. After the due date the payable amount may be doubled. Failure to pay may lead to
    further enforcement action under the Motor Vehicles Ordinance (demo notice).
    """

    evidence_path = os.path.join(EVIDENCE_DIR, ch["evidence_image"]) if ch["evidence_image"] else ""
    plate_path = os.path.join(EVIDENCE_DIR, ch["plate_crop"]) if ch["plate_crop"] else ""
    cells = []
    for path, label in (
        (evidence_path, "Violation image"),
        (plate_path, "Plate crop"),
        ("", "Violation Image 3"),
    ):
        if path and os.path.exists(path):
            cells.append(Image(path, width=60 * mm, height=32 * mm))
        else:
            cells.append(_p(f"<i>{label}</i>", small))
    media = Table([cells], colWidths=[66 * mm, 66 * mm, 66 * mm])
    media.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story = [
        header,
        Spacer(1, 3 * mm),
        notice,
        Spacer(1, 3 * mm),
        details,
        Spacer(1, 3 * mm),
        _p(legal_text, legal),
        Spacer(1, 2 * mm),
        media,
        Spacer(1, 16 * mm),
    ]

    doc = SimpleDocTemplate(
        pdf_filepath,
        pagesize=A4,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=16 * mm,
        title=f"E-Challan {challan_no}",
        author=POLICE_DEPT_NAME,
    )
    doc.build(story, onFirstPage=_draw_watermark, onLaterPages=_draw_watermark)

    if os.path.exists(qr_path):
        try:
            os.remove(qr_path)
        except OSError:
            pass

    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    cursor = conn.cursor()
    cursor.execute("UPDATE challans SET pdf_path = ? WHERE challan_no = ?", (pdf_filename, challan_no))
    conn.commit()
    conn.close()
    return pdf_filename
