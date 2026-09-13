"""Authentication endpoints for login, registration, and current-user lookup."""

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from passlib.context import CryptContext
from pydantic import BaseModel
from app.config import DB_PATH
import datetime

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLE_ALIASES = {
    "Officer": "Traffic Police Officer",
    "Admin": "Vehicle Registerer",
}

SPECIAL_ROLE_CREDENTIALS = {
    "Traffic Police Officer": {
        "officer1@example.com": "Officer@1234",
        "officer2@example.com": "Officer@5678",
    },
    "Vehicle Registerer": {
        "registrar1@example.com": "Registrar@1234",
        "registrar2@example.com": "Registrar@5678",
    },
}

class LoginRequest(BaseModel):
    email: str
    password: str
    role: str | None = None

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str | None = None
    role: str = "Citizen"

class ProfileUpdateRequest(BaseModel):
    name: str


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _canonical_role(value: str) -> str:
    role = (value or "").strip()
    return ROLE_ALIASES.get(role, role)


def _legacy_role_view(user: dict) -> dict:
    compatibility_role = {
        "Traffic Police Officer": "Officer",
        "Vehicle Registerer": "Admin",
    }.get(user["role"], user["role"])
    return {**user, "role": compatibility_role}


def _is_allowed_officer_email(conn: sqlite3.Connection, email: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM allowed_emails WHERE email = ? AND role = ?",
        (email, "Traffic Police Officer"),
    ).fetchone()
    return row is not None


def _validate_fixed_role_credentials(role: str, email: str, password: str) -> None:
    if role == "Traffic Police Officer" and not _is_fixed_officer_email(email):
        raise HTTPException(status_code=403, detail="This email is not authorized to register as a Traffic Police Officer")

    expected_password = SPECIAL_ROLE_CREDENTIALS.get(role, {}).get(email)
    if expected_password is None:
        raise HTTPException(status_code=403, detail=f"Select one of the fixed {role} accounts.")
    if password != expected_password:
        raise HTTPException(status_code=403, detail="Use the fixed password assigned to this special-role account.")


def _is_fixed_officer_email(email: str) -> bool:
    return email in SPECIAL_ROLE_CREDENTIALS["Traffic Police Officer"]


def _verify_password(password: str, stored_password: str) -> tuple[bool, bool]:
    if stored_password.startswith("$2"):
        try:
            return pwd_context.verify(password, stored_password), False
        except ValueError:
            return False, False
    return stored_password == password, True


@router.post("/login")
def login_user(req: LoginRequest, response: Response):
    # Verify credentials and create a server session.
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    requested_role = _canonical_role(req.role or "")
    email = _normalize_email(req.email)
    cursor.execute(
        "SELECT id, name, email, password, role, is_verified FROM users WHERE email = ?",
        (email,),
    )
    user = cursor.fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="No account found for this email. Please register first.")

    stored_role = _canonical_role(user["role"])
    if stored_role == "Traffic Police Officer" and not _is_allowed_officer_email(conn, email):
        conn.close()
        raise HTTPException(status_code=403, detail="This account is no longer authorized")

    if requested_role in SPECIAL_ROLE_CREDENTIALS:
        _validate_fixed_role_credentials(requested_role, email, req.password)

    password_valid, legacy_password = _verify_password(req.password, user["password"])
    if not password_valid:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email address or password.")

    if legacy_password:
        cursor.execute(
            "UPDATE users SET password = ?, role = ? WHERE id = ?",
            (pwd_context.hash(req.password), stored_role, user["id"]),
        )

    if requested_role and stored_role != requested_role:
        conn.close()
        raise HTTPException(
            status_code=403,
            detail="This account is not allowed to log in as that role. Use the correct role for your registered account.",
        )

    conn.commit()
    conn.close()

    # Public accounts are limited to the citizen portal only.
    response.set_cookie(
        key="auth_session",
        value=str(user["id"]),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    response_user = dict(user)
    response_user["role"] = stored_role
    return {"success": True, "user": response_user}

@router.post("/logout")
def logout_user(response: Response):
    response.delete_cookie("auth_session")
    return {"success": True}


@router.post("/register")
def register_user(req: RegisterRequest):
    # Public registration creates an account that can log in immediately.
    role = _canonical_role(req.role or "Citizen")
    allowed_roles = {"Citizen", "Traffic Police Officer", "Vehicle Registerer"}
    if role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Role must be one of: Citizen, Traffic Police Officer, Vehicle Registerer.")

    if req.confirm_password is not None and req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    email = _normalize_email(req.email)

    if role == "Traffic Police Officer":
        whitelist_conn = sqlite3.connect(str(DB_PATH), timeout=15)
        authorized = _is_allowed_officer_email(whitelist_conn, email)
        whitelist_conn.close()
        if not authorized:
            raise HTTPException(status_code=403, detail="This email is not authorized to register as a Traffic Police Officer")

    if role in SPECIAL_ROLE_CREDENTIALS:
        _validate_fixed_role_credentials(role, email, req.password)

    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.execute("PRAGMA busy_timeout = 15000")
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        """, (req.name.strip(), email, pwd_context.hash(req.password), role, now_str))
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

    conn = sqlite3.connect(str(DB_PATH), timeout=15)
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
    return _legacy_role_view(user)

def require_roles(*allowed_roles):
    """Build a dependency that permits only the requested database roles."""
    def dependency(request: Request):
        user = _session_user(request)
        allowed = {_canonical_role(role) for role in allowed_roles}
        if not user or _canonical_role(user["role"]) not in allowed:
            raise HTTPException(
                status_code=403,
                detail="Your account does not have access to this feature.",
            )
        return _legacy_role_view(user)
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
        allowed = {_canonical_role(role) for role in allowed_roles}
        if _canonical_role(user["role"]) not in allowed:
            raise HTTPException(
                status_code=403,
                detail="Your account does not have access to this feature.",
            )
        return _legacy_role_view(user)
    return dependency


@router.get("/users")
def list_registered_users(user: dict = Depends(require_roles("Officer"))):
    """Return account totals and registrations for Traffic Police Officers."""
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, email, role, created_at, is_verified FROM users ORDER BY created_at DESC, id DESC"
    ).fetchall()
    conn.close()

    users = [dict(row) for row in rows]
    counts = {"Citizen": 0, "Traffic Police Officer": 0, "Vehicle Registerer": 0}
    for registered_user in users:
        role = _canonical_role(registered_user["role"])
        registered_user["role"] = role
        counts[role] = counts.get(role, 0) + 1

    return {"counts": counts, "total": len(users), "users": users}


@router.delete("/users/{user_id}")
def delete_registered_user(user_id: int, user: dict = Depends(require_roles("Officer"))):
    """Remove a registered account, except the officer performing the action."""
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot remove your own active account.")

    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="Registered account not found.")
    return {"success": True, "message": "Registered account removed."}

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
