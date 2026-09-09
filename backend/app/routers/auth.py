"""Authentication endpoints for login, registration, and current-user lookup."""

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from app.config import DB_PATH
import datetime

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str
    role: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class ProfileUpdateRequest(BaseModel):
    name: str

@router.post("/login")
def login_user(req: LoginRequest, response: Response):
    # Verify credentials and create a server session.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, email, role FROM users WHERE email = ? AND password = ?", (req.email.strip().lower(), req.password))
    user = cursor.fetchone()
    conn.close()
    
    if not user or user["role"] != req.role:
        raise HTTPException(status_code=401, detail="Invalid email address or password.")

    response.set_cookie(
        key="auth_session",
        value=str(user["id"]),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return {"success": True, "user": dict(user)}

@router.post("/logout")
def logout_user(response: Response):
    response.delete_cookie("auth_session")
    return {"success": True}

@router.post("/register")
def register_user(req: RegisterRequest):
    # Public registration creates a limited citizen account.
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute("""
        INSERT INTO users (name, email, password, role, created_at)
        VALUES (?, ?, ?, 'Citizen', ?)
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
                "role": "Citizen"
            }
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")

def _session_user(request: Request):
    user_id = request.cookies.get("auth_session")
    if not user_id or not user_id.isdigit():
        return None

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    user = conn.execute(
        "SELECT id, name, email, role FROM users WHERE id = ?",
        (int(user_id),),
    ).fetchone()
    conn.close()
    return dict(user) if user else None

@router.get("/me")
def get_current_user(request: Request):
    user = _session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return {"user": user}

def require_user(request: Request):
    """Resolve the authenticated browser session to its database user."""
    user = _session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user

def require_roles(*allowed_roles):
    """Build a dependency that permits only the requested database roles."""
    def dependency(request: Request):
        user = require_user(request)
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Your account does not have access to this feature.",
            )
        return user
    return dependency

@router.patch("/profile")
def update_profile(req: ProfileUpdateRequest, user: dict = Depends(require_roles("Citizen", "Officer", "Admin"))):
    name = req.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must contain at least two characters.")
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user["id"]))
    conn.commit()
    conn.close()
    return {"success": True, "name": name}
    
def require_registered_session(request: Request):
    """Allow protected pages only when the session belongs to a database user."""
    user = _session_user(request)
    if not user:
        next_url = f"{request.url.path}?{request.url.query}" if request.url.query else request.url.path
        raise HTTPException(
            status_code=307,
            detail="Please log in with a registered account.",
            headers={"Location": f"/login?next={next_url}"},
        )

    return user["id"]
