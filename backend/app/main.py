import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import (
    STATIC_DIR, EVIDENCE_DIR, PDFS_DIR, SYSTEM_VERSION, POLICE_DEPT_NAME
)
from app.seed_data import seed_database
from app.routers import stream, challans, citizen, analytics, simulate, auth, vehicles, reports

app = FastAPI(
    title="Smart Traffic Challan & ANPR System",
    description="Automated Traffic Surveillance, Violation Detection, and E-Challan System",
    version=SYSTEM_VERSION
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed database on startup
@app.on_event("startup")
def startup_event():
    print("[System] Initializing Database & Seed Records...")
    seed_database()
    print("[System] Ready to serve.")

# Register API Routers
app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(reports.router)
app.include_router(stream.router)
app.include_router(challans.router)
app.include_router(citizen.router)
app.include_router(analytics.router)
app.include_router(simulate.router)

# Mount evidence & PDF storage directories for web access
app.mount("/evidence", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence")
app.mount("/pdfs", StaticFiles(directory=str(PDFS_DIR)), name="pdfs")

# Serve Frontend Pages matching screenshot flows
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/login")
@app.get("/login.html")
def serve_login():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))

@app.get("/register")
@app.get("/register.html")
def serve_register():
    return FileResponse(os.path.join(STATIC_DIR, "register.html"))

@app.get("/dashboard")
@app.get("/dashboard.html")
def serve_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))

@app.get("/vehicles")
@app.get("/vehicles/add")
@app.get("/vehicles.html")
def serve_vehicles():
    return FileResponse(os.path.join(STATIC_DIR, "vehicles.html"))

@app.get("/number-plate")
@app.get("/number_plate.html")
def serve_number_plate():
    return FileResponse(os.path.join(STATIC_DIR, "number_plate.html"))

@app.get("/generate-challan")
@app.get("/generate_challan.html")
def serve_generate_challan():
    return FileResponse(os.path.join(STATIC_DIR, "generate_challan.html"))

@app.get("/challan/{challan_id}")
def serve_challan_page(challan_id: str):
    return FileResponse(os.path.join(STATIC_DIR, "challan_detail.html"))

@app.get("/challans")
@app.get("/challans.html")
def serve_challans():
    return FileResponse(os.path.join(STATIC_DIR, "challans.html"))

@app.get("/reports")
@app.get("/reports.html")
def serve_reports():
    return FileResponse(os.path.join(STATIC_DIR, "reports.html"))

@app.get("/citizen.html")
def serve_citizen():
    return FileResponse(os.path.join(STATIC_DIR, "citizen.html"))

@app.get("/simulate.html")
def serve_simulate():
    return FileResponse(os.path.join(STATIC_DIR, "simulate.html"))

# Mount Frontend static assets (CSS, JS, images)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
