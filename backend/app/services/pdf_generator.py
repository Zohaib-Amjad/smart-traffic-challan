import os
import sqlite3
import datetime
import qrcode
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.config import DB_PATH, EVIDENCE_DIR, PDFS_DIR, POLICE_DEPT_NAME, HOTLINE

def generate_qr_code(challan_no: str) -> str:
    """Generates a temporary QR code image for the challan verification."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    # Verification URL for citizen portal
    verify_url = f"http://127.0.0.1:8000/citizen.html?challan={challan_no}"
    qr.add_data(verify_url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="#0F172A", back_color="white")
    qr_path = os.path.join(PDFS_DIR, f"{challan_no}_qr.png")
    qr_img.save(qr_path)
    return qr_path

def generate_challan_pdf(challan_no: str) -> str:
    """
    Generates a formal E-Challan ticket PDF.
    Returns the relative filepath to the generated PDF.
    """
    conn = sqlite3.connect(str(DB_PATH))
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
    
    doc = SimpleDocTemplate(
        pdf_filepath,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),
        alignment=1 # Center
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )
    
    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#DC2626'),
        alignment=1
    )
    
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
    )
    
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155'),
    )
    
    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A'),
    )

    # 1. Header
    story.append(Paragraph(POLICE_DEPT_NAME.upper(), title_style))
    story.append(Paragraph("AUTOMATED TRAFFIC ENFORCEMENT & SURVEILLANCE DIVISION", subtitle_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("ELECTRONIC TRAFFIC VIOLATION NOTICE (E-CHALLAN)", badge_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#DC2626'), spaceAfter=12))

    # 2. Key Info Box (Challan No, Date, Status, Fine)
    created_date = ch["created_at"]
    due_date = (datetime.datetime.strptime(created_date, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=10)).strftime("%Y-%m-%d")
    
    qr_img_path = generate_qr_code(challan_no)
    
    info_table_data = [
        [
            Paragraph(f"<b>Challan Ticket #:</b> {challan_no}", normal_style),
            Paragraph(f"<b>Notice Date:</b> {created_date}", normal_style),
            Image(qr_img_path, width=0.8*inch, height=0.8*inch)
        ],
        [
            Paragraph(f"<b>Due Date:</b> <font color='#DC2626'>{due_date}</font>", normal_style),
            Paragraph(f"<b>Status:</b> <b>{ch['status']}</b>", normal_style),
            ""
        ],
        [
            Paragraph(f"<b>Total Fine Payable:</b> <font size=11 color='#16A34A'><b>PKR {ch['fine_amount']:,}/-</b></font>", bold_style),
            Paragraph(f"<b>Helpline:</b> {HOTLINE}", normal_style),
            ""
        ]
    ]
    
    info_table = Table(info_table_data, colWidths=[2.6*inch, 2.6*inch, 1.8*inch])
    info_table.setStyle(TableStyle([
        ('SPAN', (2, 0), (2, 2)),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # 3. Vehicle & Owner Details Table
    story.append(Paragraph("1. REGISTERED VEHICLE & OWNER INFORMATION", section_style))
    story.append(Spacer(1, 4))
    
    owner_name = veh["owner_name"] if veh else "Unverified Citizen"
    owner_cnic = veh["owner_cnic"] if veh else "N/A"
    owner_phone = veh["owner_phone"] if veh else "N/A"
    owner_addr = veh["owner_address"] if veh else "Address on record"
    veh_desc = f"{veh['vehicle_make']} {veh['vehicle_model']} ({veh['vehicle_color']})" if veh else "Vehicle"

    veh_table_data = [
        [Paragraph("<b>Registration Number (Plate):</b>", normal_style), Paragraph(f"<font size=10 color='#0284C7'><b>{ch['plate_number']}</b></font>", bold_style),
         Paragraph("<b>Vehicle Make & Model:</b>", normal_style), Paragraph(veh_desc, normal_style)],
        [Paragraph("<b>Registered Owner Name:</b>", normal_style), Paragraph(owner_name, normal_style),
         Paragraph("<b>Owner CNIC #:</b>", normal_style), Paragraph(owner_cnic, normal_style)],
        [Paragraph("<b>Contact Phone:</b>", normal_style), Paragraph(owner_phone, normal_style),
         Paragraph("<b>Registered Address:</b>", normal_style), Paragraph(owner_addr, normal_style)]
    ]
    
    veh_table = Table(veh_table_data, colWidths=[1.8*inch, 1.9*inch, 1.6*inch, 1.9*inch])
    veh_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(veh_table)
    story.append(Spacer(1, 12))

    # 4. Offense & Evidence Table
    story.append(Paragraph("2. VIOLATION DETAILS & PHOTOGRAPHIC EVIDENCE", section_style))
    story.append(Spacer(1, 4))
    
    offense_table_data = [
        [Paragraph("<b>Violation Description:</b>", normal_style), Paragraph(f"<font color='#DC2626'><b>{ch['violation_name']}</b></font>", bold_style)],
        [Paragraph("<b>Location / Camera:</b>", normal_style), Paragraph(f"{ch['location']} ({ch['camera_name']})", normal_style)],
        [Paragraph("<b>Speed Recorded:</b>", normal_style), Paragraph(f"{ch['speed_detected']} km/h (Permissible Limit: {ch['speed_limit']} km/h)", normal_style)],
    ]
    
    offense_table = Table(offense_table_data, colWidths=[2.0*inch, 5.2*inch])
    offense_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(offense_table)
    story.append(Spacer(1, 8))

    # Evidence Images (Full frame + Plate crop)
    evidence_img_path = os.path.join(EVIDENCE_DIR, ch["evidence_image"]) if ch["evidence_image"] else ""
    plate_img_path = os.path.join(EVIDENCE_DIR, ch["plate_crop"]) if ch["plate_crop"] else ""
    
    img_cells = []
    if os.path.exists(evidence_img_path):
        img_cells.append(Image(evidence_img_path, width=4.2*inch, height=2.2*inch))
    else:
        img_cells.append(Paragraph("<i>[Surveillance Evidence Frame]</i>", normal_style))
        
    if os.path.exists(plate_img_path):
        img_cells.append(Image(plate_img_path, width=2.6*inch, height=1.1*inch))
    else:
        img_cells.append(Paragraph("<i>[Plate Crop]</i>", normal_style))
        
    media_table = Table([
        [Paragraph("<b>CCTV Violation Snapshot:</b>", normal_style), Paragraph("<b>ANPR Cropped Plate:</b>", normal_style)],
        [img_cells[0], img_cells[1]]
    ], colWidths=[4.4*inch, 2.8*inch])
    
    media_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(media_table)
    story.append(Spacer(1, 10))

    # 5. Payment & Dispute Instructions
    story.append(Paragraph("3. PAYMENT INSTRUCTIONS & LEGAL NOTICE", section_style))
    story.append(Spacer(1, 3))
    
    instructions = """
    <b>How to Pay:</b> You can pay this challan online via <b>JazzCash, EasyPaisa, 1Link Online Banking</b>, or at any authorized National Bank branch using Challan Number: <b>""" + challan_no + """</b>.<br/>
    <b>Dispute Resolution:</b> If you believe this citation was issued erroneously, you may file a digital dispute within 7 days at <u>http://127.0.0.1:8000/citizen.html</u>.<br/>
    <b>Warning:</b> Failure to settle the fine by the due date may result in vehicle impoundment and cancellation of driver's license under the Motor Vehicles Act.
    """
    story.append(Paragraph(instructions, normal_style))
    story.append(Spacer(1, 8))
    
    # Official Footer Stamp
    footer_text = f"<i>Generated automatically by ANPR Surveillance System v2.4 | Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7.5, textColor=colors.HexColor('#94A3B8'), alignment=1)))

    doc.build(story)
    
    # Clean up temp QR image
    if os.path.exists(qr_img_path):
        try:
            os.remove(qr_img_path)
        except Exception:
            pass
            
    # Update challan record with PDF path
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("UPDATE challans SET pdf_path = ? WHERE challan_no = ?", (pdf_filename, challan_no))
    conn.commit()
    conn.close()
    
    return pdf_filename
