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
    role: str | None = None

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "Citizen"

class ProfileUpdateRequest(BaseModel):
    name: str


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


@router.post("/login")
def login_user(req: LoginRequest, response: Response):
    # Verify credentials and create a server session.
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    requested_role = (req.role or "").strip().title()
    email = _normalize_email(req.email)
    cursor.execute(
        "SELECT id, name, email, password, role, is_verified FROM users WHERE email = ?",
        (email,),
    )
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="No account found for this email. Please register first.")

    if user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid email address or password.")

    if requested_role and user["role"] != requested_role:
        raise HTTPException(
            status_code=403,
            detail="This account is not allowed to log in as that role. Use the correct role for your registered account.",
        )

    # Public accounts are limited to the citizen portal only.
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
    # Public registration creates an account that can log in immediately.
    role = (req.role or "Citizen").strip().title()
    allowed_roles = {"Citizen", "Officer", "Admin"}
    if role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Role must be one of: Citizen, Officer, Admin.")

    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.execute("PRAGMA busy_timeout = 15000")
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email = _normalize_email(req.email)

    try:
        existing_user = cursor.execute(
            "SELECT id FROM users WHERE LOWER(email) = ?",
            (email,),
        ).fetchone()
        if existing_user:
            raise sqlite3.IntegrityError
        cursor.execute("""
        INSERT INTO users (name, email, password, role, created_at, is_verified)
        VALUES (?, ?, ?, ?, ?, 1)
        """, (req.name.strip(), email, req.password, role, now_str))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        response = {
            "success": True,
            "user": {
                "id": user_id,
                "name": req.name.strip(),
                "email": email,
                "role": role,
                "is_verified": True,
            },
            "message": "Account registered successfully. You can now log in.",
        }
        return response
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")
    except sqlite3.OperationalError as exc:
        conn.close()
        if "locked" in str(exc).lower():
            raise HTTPException(status_code=503, detail="The registration database is busy. Please try again in a few seconds.")
        raise HTTPException(status_code=500, detail="Registration could not be completed. Please try again.")

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


def require_roles_or_redirect(*allowed_roles):
    """HTML page guard: redirect guests to the login page instead of showing JSON errors."""
    def dependency(request: Request):
        user = _session_user(request)
        if not user:
            next_url = f"{request.url.path}?{request.url.query}" if request.url.query else request.url.path
            raise HTTPException(
                status_code=307,
                detail="Please sign in.",
                headers={"Location": f"/login?next={next_url}"},
            )
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
