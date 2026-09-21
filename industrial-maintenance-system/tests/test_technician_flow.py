"""
Unit & Integration Tests for Technician Portal & Mobile Notification Flow.
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
from src.services.equipment_service import EquipmentService
from src.services.work_order_service import WorkOrderService
from src.services.notification_service import NotificationService
from src.web.server import create_server


class TestTechnicianFlow(unittest.TestCase):
    """Tests for technician portal closing flow and notifications."""

    def setUp(self):
        self.test_db_path = str(BASE_DIR / "data" / "test_tech_cmms.db")
        self.db = DatabaseManager(self.test_db_path)
        self.eq_service = EquipmentService(self.db)
        self.wo_service = WorkOrderService(self.db)
        self.notif_service = NotificationService(str(BASE_DIR / "data" / "test_notif_config.json"))

        # Setup equipment and order
        self.eq_service.register_equipment("MTR-900", "Motor Extrusor", "Eléctrico", "Línea 1", 100.0)
        self.wo = self.wo_service.create_work_order(
            equipment_code="MTR-900",
            title="Cambio de rodamientos y sellos",
            description="Vibración excesiva detectada",
            assigned_technician="Ing. Carlos Mendoza",
        )

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass
        config_path = BASE_DIR / "data" / "test_notif_config.json"
        if config_path.exists():
            try:
                os.remove(config_path)
            except Exception:
                pass

    def test_technician_closing_with_work_done_and_materials(self):
        """Technician fills 'qué se hizo' and 'qué usó' upon completion."""
        # 1. Start OT
        self.wo_service.start_work_order(self.wo.id)
        started_wo = self.wo_service.get_work_order_by_id(self.wo.id)
        self.assertEqual(started_wo.status, "IN_PROGRESS")

        # 2. Close OT with technical report
        work_done = "Se desmontó la carcasa, se calibró el rotor y se colocaron rodamientos nuevos."
        materials_used = "2x Rodamientos 6205, 1x Retenedor viton, 100g grasa de litio."
        success = self.wo_service.close_work_order(
            order_id=self.wo.id,
            downtime_hours=2.5,
            cost=85.50,
            work_done=work_done,
            materials_used=materials_used,
        )
        self.assertTrue(success)

        # 3. Verify closed OT contains report in description
        closed_wo = self.wo_service.get_work_order_by_id(self.wo.id)
        self.assertEqual(closed_wo.status, "COMPLETED")
        self.assertEqual(closed_wo.downtime_hours, 2.5)
        self.assertEqual(closed_wo.cost, 85.50)
        self.assertIn("Trabajo Realizado", closed_wo.description)
        self.assertIn(work_done, closed_wo.description)
        self.assertIn("Materiales/Repuestos Usados", closed_wo.description)
        self.assertIn(materials_used, closed_wo.description)

    def test_notification_alert_generation(self):
        """Notification service formats alert with direct link for mobile."""
        direct_link = f"http://192.168.1.50:5000/tecnico?id={self.wo.id}"
        alert_entry = self.notif_service.send_work_order_alert(self.wo, direct_url=direct_link)

        self.assertEqual(alert_entry["work_order_id"], self.wo.id)
        self.assertEqual(alert_entry["technician"], "Ing. Carlos Mendoza")
        self.assertIn(direct_link, alert_entry["message"])
        self.assertIn("MTR-900", alert_entry["message"])


class TestTechnicianWebEndpoints(unittest.TestCase):
    """Tests for HTTP server technician endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.host = "127.0.0.1"
        cls.port = 58925
        cls.server = create_server(cls.host, cls.port)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_serve_tecnico_page(self):
        conn = HTTPConnection(self.host, self.port)
        conn.request("GET", "/tecnico")
        res = conn.getresponse()
        data = res.read()
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertIn(b"CMMS M\xc3\x93VIL", data)
        self.assertIn(b"Portal del T\xc3\xa9cnico", data)

    def test_network_info_endpoint(self):
        conn = HTTPConnection(self.host, self.port)
        conn.request("GET", "/api/network-info")
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertTrue(data["success"])
        self.assertIn("local_ip", data)
        self.assertIn("/tecnico", data["technician_url"])


if __name__ == "__main__":
    unittest.main()
