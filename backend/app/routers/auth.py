"""Authentication endpoints for login, registration, and current-user lookup."""

import os
import random
import smtplib
import sqlite3
import uuid
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.config import DB_PATH, HOST, PORT
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


def _generate_verification_token() -> str:
    return uuid.uuid4().hex


def _generate_verification_code() -> str:
    return str(random.randint(100000, 999999))


def _verification_link(token: str) -> str:
    return f"http://{HOST}:{PORT}/api/auth/verify?token={token}"


def send_verification_email(email: str, code: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@traffic.local")

    if smtp_host and smtp_user and smtp_pass:
        msg = EmailMessage()
        msg["Subject"] = "Smart Traffic Challan - Email Verification Code"
        msg["From"] = from_email
        msg["To"] = email
        msg.set_content(
            "Your email verification code is: " + code + "\n\n"
            "Enter this code in the application to complete your registration."
        )

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return {"sent": True, "mode": "smtp"}

    print(f"[DEV_EMAIL] Verification code for {email}: {code}")
    return {"sent": True, "mode": "dev-console", "debug_code": code}


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

    if not user["is_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Your email is not verified yet. Please check the verification link sent to your inbox before logging in.",
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
    # Public registration creates a pending account for the selected role and requires email verification.
    role = (req.role or "Citizen").strip().title()
    allowed_roles = {"Citizen", "Officer", "Admin"}
    if role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Role must be one of: Citizen, Officer, Admin.")

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email = _normalize_email(req.email)
    verification_code = _generate_verification_code()
    verification_expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute("""
        INSERT INTO users (name, email, password, role, created_at, is_verified, verification_token, verification_expires_at)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?)
        """, (req.name.strip(), email, req.password, role, now_str, verification_code, verification_expires_at))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        email_result = send_verification_email(email, verification_code)
        response = {
            "success": True,
            "user": {
                "id": user_id,
                "name": req.name.strip(),
                "email": email,
                "role": role,
                "is_verified": False,
            },
            "message": "Verification code sent to your email. Enter it below to complete registration.",
        }
        if email_result.get("mode") == "dev-console":
            response["debug_code"] = verification_code
        return response
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")


@router.post("/verify-code")
def verify_email_code(req: dict):
    email = _normalize_email(req.get("email", ""))
    code = (req.get("code") or "").strip()
    if not email or not code:
        raise HTTPException(status_code=400, detail="Email and verification code are required.")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    user = cursor.execute(
        "SELECT id, email, verification_token, verification_expires_at FROM users WHERE LOWER(email) = ?",
        (email,),
    ).fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="No account found for this email.")

    expires_at = user["verification_expires_at"]
    if not expires_at:
        conn.close()
        raise HTTPException(status_code=400, detail="This account has already been verified or does not need a code.")

    expires_dt = datetime.datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
    if expires_dt < datetime.datetime.now():
        conn.close()
        raise HTTPException(status_code=400, detail="This verification code has expired. Please register again.")

    if str(user["verification_token"]) != str(code):
        conn.close()
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    cursor.execute(
        "UPDATE users SET is_verified = 1, verification_token = NULL, verification_expires_at = NULL, email_verified_at = ? WHERE id = ?",
        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"]),
    )
    conn.commit()
    conn.close()

    return {"success": True, "message": "Email verified successfully. You can now log in.", "redirect": "/login?verified=1"}


@router.get("/verify")
def verify_email(request: Request):
    token = (request.query_params.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Verification token is missing.")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    user = cursor.execute(
        "SELECT id, name, email, role, is_verified, verification_expires_at FROM users WHERE verification_token = ?",
        (token,),
    ).fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")

    expires_at = user["verification_expires_at"]
    if expires_at:
        expires_dt = datetime.datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
        if expires_dt < datetime.datetime.now():
            conn.close()
            raise HTTPException(status_code=400, detail="This verification link has expired. Please register again and request a new confirmation code.")

    cursor.execute(
        "UPDATE users SET is_verified = 1, verification_token = NULL, verification_expires_at = NULL, email_verified_at = ? WHERE id = ?",
        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"]),
    )
    conn.commit()
    conn.close()

    return RedirectResponse(url="/login?verified=1", status_code=302)

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
