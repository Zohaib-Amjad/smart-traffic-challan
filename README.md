# Smart Traffic Challan System Using Number Plate Recognition

### Project Domain / Category
* **Artificial Intelligence (AI)**
* **Computer Vision**
* **Web Application Development**

---

## 📌 Project Overview
With the rapid increase in vehicles on roads, traffic violations have become a major concern, making manual monitoring inefficient and time-consuming. To address this issue, this project provides a **Smart Traffic Challan System** that automates violation detection using **Number Plate Recognition (NPR)**.

The system integrates **Computer Vision** techniques to capture and process images or video frames of vehicles. It then applies **Optical Character Recognition (OCR)** to extract the vehicle number plate characters from the detected region. After extraction, **Artificial Intelligence (AI)** is used to validate, match, and process the number plate information with the database to identify violations and generate automatic e-challans.

---

## 🎯 11 Functional Requirements Mapping

| # | Functional Requirement | System Implementation & Module |
|---|---|---|
| **1** | **Input Stage** | Upload vehicle image (.jpg/.png) or video stream (.mp4/.avi) as input via `/simulate.html` and REST API. |
| **2** | **Vehicle Detection** | Identifies vehicles (Sedans, SUVs, Hatchbacks, Bikes, Pickups, Buses) using OpenCV morphological & contour tracking (`detector.py`). |
| **3** | **Number Plate Detection** | Locates number plate coordinates (ROI) using aspect ratio & edge filtering (`detector.py`). |
| **4** | **Text Extraction** | Extracts alphanumeric characters using **Tesseract OCR** / **EasyOCR** (`ocr_reader.py`). |
| **5** | **Data Cleaning and Verification** | Sanitizes OCR text, resolves optical ambiguities, and verifies format against standard registration syntax (`clean_and_verify_plate_data`). |
| **6** | **Data Storage** | Stores verified vehicle, owner, and challan information in an **SQLite** database (`database.py`, `traffic_challan.db`). |
| **7** | **Violation Detection** | Analyzes vehicle data for Red Light Signal Jumping, Over-Speeding, and Wrong Lane violations (`violation_rules.py`). |
| **8** | **Challan Generation** | Automatically generates official digital e-challans with QR verification and printable PDF slips (`pdf_generator.py`). |
| **9** | **Result Display** | Presents processed pipeline stages and detection outcomes in the modern web interface. |
| **10** | **Record Management** | Maintains a complete history of issued challans with search, filtering, and status updates (`index.html`, `/api/challans`). |
| **11** | **Administrative Control** | Full admin panel for system monitoring, live camera control, speed limit adjustment, and analytics (`index.html`). |

---

## 🛠️ Tools & Technologies Used (100% Free & Open-Source)

* **Programming Language:** Python 3.11
* **Libraries:** OpenCV (`opencv-python`), NumPy, Pillow, Pydantic
* **OCR Tool:** Tesseract OCR (`pytesseract`), EasyOCR
* **Backend Framework:** FastAPI / Uvicorn (High-performance Python web framework)
* **Database:** SQLite (Embedded, zero configuration)
* **Document Engine:** ReportLab + QRCode (Official E-Challan PDF Generator)
* **Frontend:** HTML5, Modern CSS (Glassmorphism & Dark Mode), JavaScript, Chart.js

---

## 🚀 How to Run the System (1-Click Startup)

1. Double click **`run_system.bat`** in `d:\TCS`.
2. Open your browser:
   * **Administrative Control Panel**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   * **Input Stage (Image & Video Upload)**: [http://127.0.0.1:8000/simulate.html](http://127.0.0.1:8000/simulate.html)
   * **Citizen E-Challan Portal**: [http://127.0.0.1:8000/citizen.html](http://127.0.0.1:8000/citizen.html)
   * **Interactive API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
