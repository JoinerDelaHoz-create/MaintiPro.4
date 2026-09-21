"""
Authentication & Authorization (RBAC) Service.
Handles user management, PBKDF2 password hashing, session tokens, and role checking.
Pure Python standard library (hashlib, hmac, secrets) - zero external dependencies!
"""

import base64
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sys
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.database.db_manager import DatabaseManager, db_manager
from src.models.entities import User, UserRole


# Secret key for HMAC token signing (persistent or env-configurable)
SECRET_KEY = os.environ.get("CMMS_SECRET_KEY", "cmms-industrial-secure-secret-key-2026")


class AuthService:
    """Authentication and session management service."""

    def __init__(self, db: DatabaseManager = db_manager):
        self.db = db
        self.seed_default_users()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Derives a secure password hash using PBKDF2 with SHA-256."""
        key = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            iterations=100_000,
        )
        return key.hex()

    @staticmethod
    def validate_password_strength(password: str) -> None:
        """
        Validates password strength according to industrial security standards:
        - Minimum 8 characters
        - At least one uppercase letter (A-Z)
        - At least one lowercase letter (a-z)
        - At least one number or special character
        """
        if not password or len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        if not any(c.isupper() for c in password):
            raise ValueError("La contraseña debe incluir al menos una letra mayúscula (A-Z).")
        if not any(c.islower() for c in password):
            raise ValueError("La contraseña debe incluir al menos una letra minúscula (a-z).")
        if not any(c.isdigit() or not c.isalnum() for c in password):
            raise ValueError("La contraseña debe incluir al menos un número o símbolo especial.")

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Changes user password after validating current password and ensuring
        the new password meets all security strength requirements.
        """
        self.validate_password_strength(new_password)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Usuario no encontrado.")

            salt = row["salt"]
            expected_hash = row["password_hash"]
            actual_hash = self._hash_password(current_password, salt)

            if not hmac.compare_digest(expected_hash, actual_hash):
                raise ValueError("La contraseña actual es incorrecta.")

            if current_password == new_password:
                raise ValueError("La nueva contraseña no puede ser igual a la actual.")

            new_salt = secrets.token_hex(16)
            new_hash = self._hash_password(new_password, new_salt)

            cursor.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (new_hash, new_salt, user_id),
            )
            conn.commit()
            return True

    def seed_default_users(self) -> None:
        """Populates the database with default accounts if no users exist."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            row = cursor.fetchone()
            if row and row["count"] > 0:
                return

            default_accounts = [
                ("admin", "admin123", "Administrador de Planta", UserRole.ADMIN.value),
                ("carlos", "1234", "Ing. Carlos Mendoza", UserRole.TECHNICIAN.value),
                ("laura", "1234", "Tec. Laura Ramos", UserRole.TECHNICIAN.value),
                ("andres", "1234", "Tec. Andrés Silva", UserRole.TECHNICIAN.value),
            ]

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for username, raw_pass, full_name, role in default_accounts:
                salt = secrets.token_hex(16)
                pwd_hash = self._hash_password(raw_pass, salt)
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, salt, full_name, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (username, pwd_hash, salt, full_name, role, now),
                )
            conn.commit()

    def register_user(self, username: str, password: str, full_name: str, role: str = UserRole.TECHNICIAN.value) -> User:
        """Registers a new user into the system."""
        username = username.strip().lower()
        full_name = full_name.strip()
        role = role.strip().upper()

        if not username or not password or not full_name:
            raise ValueError("Usuario, contraseña y nombre completo son obligatorios.")

        if role not in (UserRole.ADMIN.value, UserRole.TECHNICIAN.value):
            raise ValueError(f"Rol inválido: '{role}'. Debe ser ADMIN o TECHNICIAN.")

        salt = secrets.token_hex(16)
        pwd_hash = self._hash_password(password, salt)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, salt, full_name, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (username, pwd_hash, salt, full_name, role, now),
                )
                user_id = cursor.lastrowid
                conn.commit()
            except Exception as err:
                if "UNIQUE" in str(err).upper():
                    raise ValueError(f"El nombre de usuario '{username}' ya está en uso.")
                raise err

        return User(
            id=user_id,
            username=username,
            password_hash=pwd_hash,
            salt=salt,
            full_name=full_name,
            role=role,
            created_at=now,
        )

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticates credentials. Returns user payload and signed auth token if valid,
        None if invalid.
        """
        username = username.strip().lower()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()

        if not row:
            return None

        salt = row["salt"]
        expected_hash = row["password_hash"]
        actual_hash = self._hash_password(password, salt)

        if not hmac.compare_digest(expected_hash, actual_hash):
            return None

        user = User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            full_name=row["full_name"],
            role=row["role"],
            created_at=row["created_at"],
        )

        token = self.generate_token(user)
        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
            },
        }

    @staticmethod
    def generate_token(user: User) -> str:
        """Generates an HMAC-signed stateless session token."""
        payload = {
            "uid": user.id,
            "usr": user.username,
            "rol": user.role,
            "nam": user.full_name,
            "ts": datetime.now().isoformat(),
        }
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

        sig = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{b64_payload}.{sig}"

    def get_user_from_token(self, token: str) -> Optional[User]:
        """Validates a signed token and returns corresponding User if valid."""
        if not token or "." not in token:
            return None

        parts = token.split(".", 1)
        if len(parts) != 2:
            return None

        b64_payload, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        try:
            # Add back base64 padding if needed
            pad = len(b64_payload) % 4
            if pad:
                b64_payload += "=" * (4 - pad)
            payload_raw = base64.urlsafe_b64decode(b64_payload.encode("utf-8")).decode("utf-8")
            payload = json.loads(payload_raw)
            username = payload.get("usr")
            if not username:
                return None

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    return None
                return User(
                    id=row["id"],
                    username=row["username"],
                    password_hash=row["password_hash"],
                    salt=row["salt"],
                    full_name=row["full_name"],
                    role=row["role"],
                    created_at=row["created_at"],
                )
        except Exception:
            return None

    def get_all_technicians(self) -> List[Dict[str, Any]]:
        """Returns list of all technicians for assignment selectors."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, full_name FROM users WHERE role = ? ORDER BY full_name ASC",
                (UserRole.TECHNICIAN.value,),
            )
            rows = cursor.fetchall()
            return [{"id": r["id"], "username": r["username"], "full_name": r["full_name"]} for r in rows]
