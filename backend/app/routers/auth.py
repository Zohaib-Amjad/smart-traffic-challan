import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.config import DB_PATH
import datetime

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

@router.post("/login")
def login_user(req: LoginRequest):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, email, role FROM users WHERE email = ? AND password = ?", (req.email.strip().lower(), req.password))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        # Check if default admin account
        if req.email.strip().lower() == "officer@traffic.gov.pk" and req.password in ["admin123", "password123"]:
            return {
                "success": True,
                "user": {
                    "id": 1,
                    "name": "Traffic Officer",
                    "email": "officer@traffic.gov.pk",
                    "role": "Officer"
                }
            }
        raise HTTPException(status_code=401, detail="Invalid email address or password.")
        
    return {"success": True, "user": dict(user)}

@router.post("/register")
def register_user(req: RegisterRequest):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute("""
        INSERT INTO users (name, email, password, role, created_at)
        VALUES (?, ?, ?, 'Officer', ?)
        """, (req.name.strip(), req.email.strip().lower(), req.password, now_str))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return {
            "success": True,
            "user": {
                "id": user_id,
                "name": req.name,
                "email": req.email,
                "role": "Officer"
            }
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")

@router.get("/me")
def get_current_user():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role FROM users LIMIT 1")
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"user": dict(user)}
    return {"user": {"id": 1, "name": "Traffic Officer", "email": "officer@traffic.gov.pk", "role": "Officer"}}
