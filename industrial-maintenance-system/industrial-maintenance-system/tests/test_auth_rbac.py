"""
Unit & Integration Tests for CMMS Authentication & Role-Based Access Control (RBAC).
"""

from http.client import HTTPConnection
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.database.db_manager import DatabaseManager
from src.services.auth_service import AuthService
from src.services.equipment_service import EquipmentService
from src.services.work_order_service import WorkOrderService
from src.models.entities import UserRole
from src.web.server import create_server


class TestAuthRBAC(unittest.TestCase):
    """Tests for authentication, authorization, and technician OT filtering."""

    def setUp(self):
        self.test_db_path = str(BASE_DIR / "data" / "test_auth_cmms.db")
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

        self.db = DatabaseManager(self.test_db_path)
        self.auth_service = AuthService(self.db)
        self.eq_service = EquipmentService(self.db)
        self.wo_service = WorkOrderService(self.db)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_seed_default_users(self):
        """Seed creates admin and default technicians."""
        admin = self.auth_service.authenticate("admin", "admin123")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["user"]["role"], UserRole.ADMIN.value)

        carlos = self.auth_service.authenticate("carlos", "1234")
        self.assertIsNotNone(carlos)
        self.assertEqual(carlos["user"]["role"], UserRole.TECHNICIAN.value)
        self.assertEqual(carlos["user"]["full_name"], "Ing. Carlos Mendoza")

    def test_invalid_login(self):
        """Invalid passwords or non-existent usernames return None."""
        self.assertIsNone(self.auth_service.authenticate("admin", "wrongpassword"))
        self.assertIsNone(self.auth_service.authenticate("nonexistent", "1234"))

    def test_token_validation(self):
        """Signed HMAC token verifies and returns corresponding User."""
        res = self.auth_service.authenticate("carlos", "1234")
        token = res["token"]
        user = self.auth_service.get_user_from_token(token)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "carlos")
        self.assertEqual(user.full_name, "Ing. Carlos Mendoza")

        # Tampered token
        tampered = token[:-4] + "xxxx"
        self.assertIsNone(self.auth_service.get_user_from_token(tampered))

    def test_technician_ot_filtering(self):
        """Technician sees only their assigned OTs and unassigned/public OTs."""
        self.eq_service.register_equipment("EQ-1", "Bomba 1", "Mecánico", "Planta", 10.0)

        # 1. OT for Carlos
        self.wo_service.create_work_order(
            "EQ-1", "OT de Carlos", "Detalle", assigned_technician="Ing. Carlos Mendoza"
        )
        # 2. OT for Laura
        self.wo_service.create_work_order(
            "EQ-1", "OT de Laura", "Detalle", assigned_technician="Tec. Laura Ramos"
        )
        # 3. Unassigned OT
        self.wo_service.create_work_order(
            "EQ-1", "OT Disponible", "Detalle", assigned_technician="Sin Asignar"
        )

        # Query for Carlos
        carlos_ots = self.wo_service.get_work_orders_for_technician("Ing. Carlos Mendoza")
        carlos_titles = [ot.title for ot in carlos_ots]
        self.assertIn("OT de Carlos", carlos_titles)
        self.assertIn("OT Disponible", carlos_titles)
        self.assertNotIn("OT de Laura", carlos_titles)

        # Query for Laura
        laura_ots = self.wo_service.get_work_orders_for_technician("Tec. Laura Ramos")
        laura_titles = [ot.title for ot in laura_ots]
        self.assertIn("OT de Laura", laura_titles)
        self.assertIn("OT Disponible", laura_titles)
        self.assertNotIn("OT de Carlos", laura_titles)

        # Admin gets all 3
        all_ots = self.wo_service.get_all_work_orders()
        self.assertEqual(len(all_ots), 3)

    def test_claim_work_order(self):
        """Technician can claim an unassigned work order."""
        self.eq_service.register_equipment("EQ-2", "Torno 2", "Mecánico", "Taller", 50.0)
        wo = self.wo_service.create_work_order(
            "EQ-2", "Avería general", "Fuga de aceite", assigned_technician="Sin Asignar"
        )

        claimed = self.wo_service.claim_work_order(wo.id, "Tec. Andrés Silva")
        self.assertTrue(claimed)

        updated_wo = self.wo_service.get_work_order_by_id(wo.id)
        self.assertEqual(updated_wo.assigned_technician, "Tec. Andrés Silva")
        self.assertEqual(updated_wo.status, "IN_PROGRESS")

    def test_password_strength_validation(self):
        """Tests security rules for strong passwords."""
        # Too short (< 8 chars)
        with self.assertRaises(ValueError):
            self.auth_service.validate_password_strength("Short1!")
        # Missing uppercase
        with self.assertRaises(ValueError):
            self.auth_service.validate_password_strength("lowercase123")
        # Missing lowercase
        with self.assertRaises(ValueError):
            self.auth_service.validate_password_strength("UPPERCASE123")
        # Missing digit or symbol
        with self.assertRaises(ValueError):
            self.auth_service.validate_password_strength("NoNumbersHere")
        # Valid strong password
        self.auth_service.validate_password_strength("SecurePass123!")

    def test_change_password_flow(self):
        """User can change password with valid current password and strong new password."""
        admin = self.auth_service.authenticate("admin", "admin123")
        user_id = admin["user"]["id"]

        # Wrong current password fails
        with self.assertRaises(ValueError):
            self.auth_service.change_password(user_id, "wrong123", "NewSecret2026!")

        # Same password fails
        with self.assertRaises(ValueError):
            self.auth_service.change_password(user_id, "admin123", "admin123")

        # Weak new password fails
        with self.assertRaises(ValueError):
            self.auth_service.change_password(user_id, "admin123", "weak")

        # Success with strong new password
        success = self.auth_service.change_password(user_id, "admin123", "SuperAdmin2026!")
        self.assertTrue(success)

        # Old password no longer works
        self.assertIsNone(self.auth_service.authenticate("admin", "admin123"))
        # New password works
        new_auth = self.auth_service.authenticate("admin", "SuperAdmin2026!")
        self.assertIsNotNone(new_auth)


if __name__ == "__main__":
    unittest.main()
