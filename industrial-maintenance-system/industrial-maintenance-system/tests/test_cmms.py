"""
Automated Test Suite for Industrial CMMS.
Tests Database, Services, Work Orders, KPIs, Exports, and IoT Telemetry.
"""

import os
import sys
import unittest
from pathlib import Path

# Set up paths
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from src.database.db_manager import DatabaseManager
from src.models.entities import EquipmentStatus, MaintenanceType, Priority, WorkOrderStatus
from src.services.equipment_service import EquipmentService
from src.services.work_order_service import WorkOrderService
from src.services.metrics_service import MetricsService
from src.services.export_service import ExportService
from src.services.iot_service import IoTService


class TestIndustrialCMMS(unittest.TestCase):
    """Integration and unit tests for CMMS core services."""

    def setUp(self):
        # Use an isolated test database
        self.test_db_path = str(base_dir / "data" / "test_cmms.db")
        self.db = DatabaseManager(self.test_db_path)
        self.eq_service = EquipmentService(self.db)
        self.wo_service = WorkOrderService(self.db)
        self.metrics_service = MetricsService(self.db)
        self.export_service = ExportService(self.db)
        self.iot_service = IoTService(self.db, wo_service=self.wo_service)

        # Ensure all tables are completely empty before each test
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM telemetry_logs;")
            conn.execute("DELETE FROM work_orders;")
            conn.execute("DELETE FROM equipments;")
            conn.commit()

    def tearDown(self):
        # Clean up test database file
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_equipment_crud(self):
        """Test equipment registration, search, update and deletion."""
        # 1. Create
        eq = self.eq_service.register_equipment(
            code="MTR-001",
            name="Motor Inducción 50HP",
            eq_type="Eléctrico",
            location="Molino A",
            operating_hours=1200.0,
        )
        self.assertEqual(eq.code, "MTR-001")
        self.assertEqual(eq.status, EquipmentStatus.OPERATIONAL.value)

        # Duplicate code prevention
        with self.assertRaises(ValueError):
            self.eq_service.register_equipment("MTR-001", "Otro", "X", "Y")

        # 2. Read & Search
        found = self.eq_service.get_equipment_by_code("MTR-001")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Motor Inducción 50HP")

        search_results = self.eq_service.search_equipments("Molino")
        self.assertEqual(len(search_results), 1)

        # 3. Update
        updated = self.eq_service.update_equipment(
            code="MTR-001",
            location="Molino B",
            operating_hours=1500.0,
        )
        self.assertTrue(updated)
        refetched = self.eq_service.get_equipment_by_code("MTR-001")
        self.assertEqual(refetched.location, "Molino B")
        self.assertEqual(refetched.operating_hours, 1500.0)

        # 4. Delete
        deleted = self.eq_service.delete_equipment("MTR-001")
        self.assertTrue(deleted)
        self.assertIsNone(self.eq_service.get_equipment_by_code("MTR-001"))

    def test_work_order_lifecycle(self):
        """Test Work Order workflow: PENDING -> IN_PROGRESS -> COMPLETED."""
        # Register equipment first
        self.eq_service.register_equipment("BMB-500", "Bomba de Vacío", "Neumático", "Zona 3", 800.0)

        # Create Work Order
        wo = self.wo_service.create_work_order(
            equipment_code="BMB-500",
            title="Falla de Rodamiento",
            description="Ruido anormal en rodamiento delantero",
            order_type=MaintenanceType.CORRECTIVE.value,
            priority=Priority.HIGH.value,
            assigned_technician="Ing. Martínez",
        )
        self.assertEqual(wo.status, WorkOrderStatus.PENDING.value)

        # Start Work Order
        self.wo_service.start_work_order(wo.id)
        eq_in_maint = self.eq_service.get_equipment_by_code("BMB-500")
        self.assertEqual(eq_in_maint.status, EquipmentStatus.MAINTENANCE.value)

        # Close Work Order with downtime and cost
        self.wo_service.close_work_order(wo.id, downtime_hours=3.5, cost=420.0)
        closed_wo = self.wo_service.get_work_order_by_id(wo.id)
        self.assertEqual(closed_wo.status, WorkOrderStatus.COMPLETED.value)
        self.assertEqual(closed_wo.downtime_hours, 3.5)
        self.assertEqual(closed_wo.cost, 420.0)

        # Equipment should return to OPERATIONAL
        eq_restored = self.eq_service.get_equipment_by_code("BMB-500")
        self.assertEqual(eq_restored.status, EquipmentStatus.OPERATIONAL.value)

    def test_metrics_calculation(self):
        """Test calculation of MTBF, MTTR, and Availability."""
        # Setup: 1 equipment with 1000 operating hours
        self.eq_service.register_equipment("CMP-TEST", "Compresor", "Neumático", "Planta", 1000.0)

        # Create and close 2 corrective work orders: Total downtime = 20h
        wo1 = self.wo_service.create_work_order(
            "CMP-TEST", "Falla 1", "Fuga", MaintenanceType.CORRECTIVE.value, Priority.HIGH.value
        )
        self.wo_service.close_work_order(wo1.id, downtime_hours=10.0, cost=200.0)

        wo2 = self.wo_service.create_work_order(
            "CMP-TEST", "Falla 2", "Válvula rota", MaintenanceType.CORRECTIVE.value, Priority.HIGH.value
        )
        self.wo_service.close_work_order(wo2.id, downtime_hours=10.0, cost=300.0)

        kpis = self.metrics_service.get_plant_kpis()
        self.assertEqual(kpis["corrective_failures"], 2)
        self.assertEqual(kpis["corrective_downtime_hours"], 20.0)
        self.assertEqual(kpis["total_cost"], 500.0)

        # MTBF = 1000 / 2 = 500 h
        self.assertEqual(kpis["mtbf_hours"], 500.0)
        # MTTR = 20 / 2 = 10 h
        self.assertEqual(kpis["mttr_hours"], 10.0)
        # Availability = (500 / (500 + 10)) * 100 = 98.04%
        expected_avail = round((500.0 / 510.0) * 100, 2)
        self.assertEqual(kpis["availability_pct"], expected_avail)

    def test_iot_telemetry_and_predictive_alerts(self):
        """Test telemetry recording and automatic predictive work order generation on anomaly."""
        self.eq_service.register_equipment("MTR-IOT", "Motor Monitoreado", "Eléctrico", "Línea 1")

        # 1. Normal reading
        reading_normal, sev_normal, wo_id_normal = self.iot_service.simulate_telemetry_reading(
            "MTR-IOT", inject_anomaly=False
        )
        self.assertEqual(sev_normal, "NORMAL")
        self.assertIsNone(wo_id_normal)

        # 2. Anomalous reading (critical vibration or temperature)
        reading_crit, sev_crit, wo_id_crit = self.iot_service.simulate_telemetry_reading(
            "MTR-IOT", inject_anomaly=True
        )
        self.assertEqual(sev_crit, "CRITICAL")
        self.assertIsNotNone(wo_id_crit)

        # Verify predictive work order was automatically registered
        auto_wo = self.wo_service.get_work_order_by_id(wo_id_crit)
        self.assertEqual(auto_wo.equipment_code, "MTR-IOT")
        self.assertEqual(auto_wo.type, MaintenanceType.PREDICTIVE.value)
        self.assertEqual(auto_wo.priority, Priority.CRITICAL.value)

    def test_export_service(self):
        """Test exporting equipments and work orders to CSV."""
        self.eq_service.register_equipment("EXP-01", "Equipo Exportar", "General", "Línea 4")
        eq_file, wo_file = self.export_service.export_all_to_csv()

        self.assertTrue(os.path.exists(eq_file))
        self.assertTrue(os.path.exists(wo_file))
        self.assertGreater(os.path.getsize(eq_file), 0)


if __name__ == "__main__":
    unittest.main()
