# Smart Traffic Challan System

Smart Traffic Challan System is a local FastAPI web application for traffic officers. It combines vehicle registration, number plate recognition, OCR, Punjab fine lookup, e-challan generation, payment-status simulation, PDF printing, and reports.

This is a final-year project and local demonstration system. It is not a live police CCTV platform and it does not process real online payments.

## Quick Start

### Windows launcher

Double-click `run_system.bat`. It creates or reuses `.venv`, installs packages when needed, starts the API, and opens the browser.

### Manual Windows start

Requirements: Python 3.10 or 3.11, Tesseract OCR, and Chrome or Edge.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/`. API docs: `http://127.0.0.1:8000/docs`.

### Docker

```powershell
docker build -t smart-traffic-challan .
docker run --rm -p 8000:7860 -e PORT=7860 smart-traffic-challan
```

Open `http://127.0.0.1:8000/`.

## Roles and User Flow

The system has three roles:

- **Citizen:** public sign-up role. Can use AI Vehicle Check, view challans linked to the account email, and use the simulated payment flow. Cannot register vehicles or generate challans.
- **Traffic Police Officer:** can use number plate recognition, generate challans, inspect challan history, and view reports.
- **Vehicle Registrar:** can register, update, search, transfer ownership, record or verify documents, and suspend or block vehicles. It cannot open the dashboard, number plate recognition, reports, or challan workflows.

Only the seeded Officer and Admin accounts have administrative privileges. Public registration can never create a privileged account.

1. Open the concise public home page.
2. Choose AI Vehicle Check, Traffic Rules, Login, or Sign up.
3. Sign in. The server creates an eight-hour HttpOnly `auth_session` cookie and resolves the database role for every protected request.
4. The browser navigation shows only the workflows allowed for that role.
5. Log out to remove browser identity data and the server session.

Guests cannot open administrative HTML pages. Direct requests redirect to `/login?next=...`. The backend checks that the session belongs to a real row in `users`.

## Pages

| Page | URL | Purpose |
| --- | --- | --- |
| Home | `/` | Public entry page with AI Vehicle Check and Traffic Rules |
| Traffic Rules | `/traffic-rules` | Public road-safety guide |
| Login | `/login` | Authenticate a registered user |
| Register | `/register` | Create an Officer account |
| Dashboard | `/dashboard` | Four-module Administrative Control hub |
| Vehicles | `/vehicles` | Vehicle Registerer registration; Officer read-only list with challan actions |
| Number Plate | `/number-plate` | Citizen portal and role-aware image upload/ANPR/OCR |
| Generate Challan | `/generate-challan` | Officer-only ticket creation from a Punjab offence |
| Challan History | `/challans` | Show tickets issued by the current user |
| Challan Detail | `/challan/{id}` | View, pay-simulate, print, or download a ticket |
| Reports | `/reports` | System-wide totals, grouping, recent tickets, and CSV |

`/citizen` and `/simulate.html` redirect to home. Their old backend code remains for compatibility but is not part of the current UI.

## Vehicle Management

`POST /api/vehicles/add` saves plate, owner, and vehicle fields. Plates are uppercase. Adding an existing plate updates its row. User-created records have `source='user'` and appear in the vehicle list.

`GET /api/vehicles/{plate_number}` looks in the registry and archive mapping. A new plate with at least four alphanumeric characters can receive a stable synthetic owner. This is not an official identity lookup.

The current form does not ask for engine capacity. New light vehicles can therefore use the schedule default of 1600cc for fine calculation.

## Number Plate Recognition

The page sends an image to `POST /api/simulate/process_image`.

1. OpenCV decodes the upload.
2. Archive images are matched by filename or hash when possible.
3. Archive XML boxes provide the plate crop.
4. Other images use Haar Cascade and contour checks.
5. Multiple vehicle or plate regions are rejected instead of selected randomly.
6. The crop is preprocessed and read by Tesseract.
7. EasyOCR can be used as a fallback.
8. Text is cleaned and validated.
9. Owner and ticket status are looked up.

The frontend waits up to ten seconds. Outcomes are a plate value, `Not found`, or `Multiple vehicles detected`. The current page does not automatically issue a challan; the officer continues to Generate Challan.

The archive contains 433 public images and XML plate boxes. A single `archive/images/Cars*.png` image can be used for testing.

## Challan Generation and Lifecycle

The Generate Challan page loads offences from `GET /api/challans/schedule?vehicle_type=&engine_cc=`. The officer selects a plate, offence, location, and due date. The browser sends the offence code to `POST /api/challans/generate`.

The backend verifies the session user, vehicle class, offence applicability, and due date. It calculates the fine from the Punjab schedule and saves the ticket with `status='Unpaid'`. A submitted fine amount is not trusted. Past due dates are rejected.

API lifecycle:

- Create: `POST /api/challans/generate`
- List: `GET /api/challans`
- Detail: `GET /api/challans/{id_or_challan_no}`
- Status: `PATCH /api/challans/{id_or_challan_no}/status`
- Delete: `DELETE /api/challans/{id_or_challan_no}`
- PDF: `GET /api/challans/{challan_no}/pdf`
- QR: `GET /api/challans/{challan_no}/qr`
- CSV: `GET /api/challans/export/csv`

History filters by `issued_by=currentUser.id`, so it shows the current user's tickets. Reports summarize every challan. Mark as Paid is a simulation and does not contact a payment gateway.

## Punjab Fine Schedule

`backend/app/punjab_schedule.py` contains offences `V-01` through `V-25` and five fine brackets:

1. Motorcycle
2. Three-wheeler
3. Motorcar or Jeep under 2000cc
4. Motorcar or Jeep over 2000cc
5. PSV, carrier, HTV, tractor, or trailer

The amount is calculated from offence plus vehicle class. Some offences are not applicable to every class. The frontend disables N/A offences and the backend performs the same validation.

## Reports

The page calls `GET /api/reports/summary`. The endpoint reads the SQLite `challans` table and calculates total challans, total fine, paid and unpaid fine, paid and unpaid counts, violation counts grouped by `violation_name`, and the ten newest rows.

`GET /api/reports/csv` exports all challans. Reports are system-wide, not limited to the logged-in officer.

Role lifecycle APIs include profile updates, citizen notifications and disputes, officer dispute review, registry search and history, ownership transfer, document verification, and vehicle registration status changes.

## Database and Startup

The database is `backend/traffic_challan.db`. Important tables are `users`, `vehicles`, `challans`, `cameras`, `archive_images`, `vehicle_types`, `violations`, `fines`, and `system_logs`.

Startup creates missing tables and refreshes reference data. It does not seed demo users or sample challans. Users are created through registration. Archive and demo vehicle records may be available for lookup but are not login accounts.

## Project Structure

```text
backend/app/main.py                 FastAPI app, startup, page routes
backend/app/database.py             SQLite schema and initialization
backend/app/config.py               Paths and settings
backend/app/routers/auth.py         Registration, login, session checks
backend/app/routers/vehicles.py     Vehicle registry APIs
backend/app/routers/challans.py     Challan APIs and lifecycle
backend/app/routers/reports.py      Reports and CSV APIs
backend/app/routers/simulate.py     Image and video processing APIs
backend/app/anpr/                   Detection, OCR, tracking, rules
backend/app/services/               Archive registry and PDF generation
frontend/                           HTML pages and browser JavaScript
archive/                            Images and XML annotations
run_system.bat                      Windows launcher
Dockerfile                          Container deployment
```

## Technology

Python, FastAPI, Uvicorn, Pydantic, SQLite, OpenCV, NumPy, Pillow, Tesseract, EasyOCR, ReportLab, qrcode, HTML, CSS, JavaScript, and Docker.

## Known Limitations

- Passwords are stored as plain text; production must use password hashing.
- The session cookie contains a user ID rather than a signed session token.
- Legacy API routes still need the same authorization treatment as protected HTML pages.
- Reports are global while history is per issuer.
- User vehicles are not associated with a particular officer in the schema.
- OCR can fail with blur, glare, poor lighting, or angled plates.
- Dummy owner data is synthetic.
- There is no live CCTV UI or real payment gateway.
- SQLite is suitable for this local project, not a multi-server production deployment without further design.

## Handover

Include `backend`, `frontend`, `archive`, `README.md`, `VIVA_GUIDE_ROMAN_URDU.txt`, `Dockerfile`, `run_system.bat`, and `backend/requirements.txt`. Do not include `.venv`, `__pycache__`, or generated uploads unless a pre-filled local database is required.
