"""
Work Order Service: Business logic for managing Maintenance Work Orders (OT).
"""

from datetime import datetime
from typing import List, Optional
from ..database.db_manager import db_manager
from ..models.entities import (
    EquipmentStatus,
    MaintenanceType,
    Priority,
    WorkOrder,
    WorkOrderStatus,
)


class WorkOrderService:
    """Handles creation, tracking, and closing of industrial Work Orders."""

    def __init__(self, db=db_manager):
        self.db = db

    def create_work_order(
        self,
        equipment_code: str,
        title: str,
        description: str,
        order_type: str = MaintenanceType.PREVENTIVE.value,
        priority: str = Priority.MEDIUM.value,
        assigned_technician: str = "Técnico de Turno",
    ) -> WorkOrder:
        """
        Creates a new maintenance work order.
        Validates that equipment exists and sets status to PENDING.
        """
        equipment_code = equipment_code.strip().upper()
        title = title.strip()
        description = description.strip()

        if not equipment_code or not title:
            raise ValueError("El código del equipo y el título de la orden son obligatorios.")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Verify equipment existence
            cursor.execute("SELECT code FROM equipments WHERE code = ?", (equipment_code,))
            if not cursor.fetchone():
                raise ValueError(f"No existe ningún equipo con código '{equipment_code}'.")

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = WorkOrderStatus.PENDING.value

            cursor.execute(
                """
                INSERT INTO work_orders (
                    equipment_code, title, description, type, priority, status,
                    assigned_technician, downtime_hours, cost, created_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, ?, NULL)
                """,
                (
                    equipment_code,
                    title,
                    description,
                    order_type.upper(),
                    priority.upper(),
                    status,
                    assigned_technician.strip(),
                    created_at,
                ),
            )
            order_id = cursor.lastrowid
            conn.commit()

        return WorkOrder(
            id=order_id,
            equipment_code=equipment_code,
            title=title,
            description=description,
            type=order_type.upper(),
            priority=priority.upper(),
            status=status,
            assigned_technician=assigned_technician,
            downtime_hours=0.0,
            cost=0.0,
            created_at=created_at,
            closed_at=None,
        )

    def get_all_work_orders(self, status_filter: Optional[str] = None) -> List[WorkOrder]:
        """Returns work orders, optionally filtered by status."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if status_filter:
                cursor.execute(
                    "SELECT * FROM work_orders WHERE status = ? ORDER BY id DESC",
                    (status_filter.strip().upper(),),
                )
            else:
                cursor.execute("SELECT * FROM work_orders ORDER BY id DESC")

            rows = cursor.fetchall()
            return [
                WorkOrder(
                    id=r["id"],
                    equipment_code=r["equipment_code"],
                    title=r["title"],
                    description=r["description"] or "",
                    type=r["type"],
                    priority=r["priority"],
                    status=r["status"],
                    assigned_technician=r["assigned_technician"] or "Sin Asignar",
                    downtime_hours=r["downtime_hours"],
                    cost=r["cost"],
                    created_at=r["created_at"],
                    closed_at=r["closed_at"],
                )
                for r in rows
            ]

    def get_work_order_by_id(self, order_id: int) -> Optional[WorkOrder]:
        """Retrieves a single work order by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM work_orders WHERE id = ?", (int(order_id),))
            row = cursor.fetchone()
            if row:
                return WorkOrder(
                    id=row["id"],
                    equipment_code=row["equipment_code"],
                    title=row["title"],
                    description=row["description"] or "",
                    type=row["type"],
                    priority=row["priority"],
                    status=row["status"],
                    assigned_technician=row["assigned_technician"] or "Sin Asignar",
                    downtime_hours=row["downtime_hours"],
                    cost=row["cost"],
                    created_at=row["created_at"],
                    closed_at=row["closed_at"],
                )
            return None

    def get_work_orders_by_equipment(self, equipment_code: str) -> List[WorkOrder]:
        """Returns all work orders associated with a specific equipment."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM work_orders WHERE equipment_code = ? ORDER BY id DESC",
                (equipment_code.strip().upper(),),
            )
            rows = cursor.fetchall()
            return [
                WorkOrder(
                    id=r["id"],
                    equipment_code=r["equipment_code"],
                    title=r["title"],
                    description=r["description"] or "",
                    type=r["type"],
                    priority=r["priority"],
                    status=r["status"],
                    assigned_technician=r["assigned_technician"] or "Sin Asignar",
                    downtime_hours=r["downtime_hours"],
                    cost=r["cost"],
                    created_at=r["created_at"],
                    closed_at=r["closed_at"],
                )
                for r in rows
            ]

    def start_work_order(self, order_id: int) -> bool:
        """
        Transitions a work order to IN_PROGRESS and updates equipment status to MAINTENANCE.
        """
        wo = self.get_work_order_by_id(order_id)
        if not wo:
            return False

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE work_orders SET status = ? WHERE id = ?",
                (WorkOrderStatus.IN_PROGRESS.value, order_id),
            )
            # Update equipment status
            cursor.execute(
                "UPDATE equipments SET status = ? WHERE code = ?",
                (EquipmentStatus.MAINTENANCE.value, wo.equipment_code),
            )
            conn.commit()
            return True

    def close_work_order(
        self,
        order_id: int,
        downtime_hours: float = 0.0,
        cost: float = 0.0,
        work_done: Optional[str] = None,
        materials_used: Optional[str] = None,
    ) -> bool:
        """
        Closes a work order as COMPLETED, records downtime hours and costs,
        and restores equipment to OPERATIONAL if no other active OTs exist.
        Optionally records technician report (work done and materials/parts used).
        """
        wo = self.get_work_order_by_id(order_id)
        if not wo:
            return False

        closed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build technician closing report if provided
        updated_description = wo.description or ""
        report_sections = []
        if work_done and work_done.strip():
            report_sections.append(f"• Trabajo Realizado: {work_done.strip()}")
        if materials_used and materials_used.strip():
            report_sections.append(f"• Materiales/Repuestos Usados: {materials_used.strip()}")

        if report_sections:
            report_text = "\n\n--- INFORME DE CIERRE TÉCNICO ---\n" + "\n".join(report_sections)
            updated_description = (updated_description + report_text).strip()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE work_orders 
                SET status = ?, downtime_hours = ?, cost = ?, closed_at = ?, description = ?
                WHERE id = ?
                """,
                (
                    WorkOrderStatus.COMPLETED.value,
                    max(0.0, float(downtime_hours)),
                    max(0.0, float(cost)),
                    closed_at,
                    updated_description,
                    order_id,
                ),
            )

            # Check if there are other pending or in-progress orders for this machine
            cursor.execute(
                """
                SELECT COUNT(*) as active_count FROM work_orders 
                WHERE equipment_code = ? AND status IN ('PENDING', 'IN_PROGRESS') AND id != ?
                """,
                (wo.equipment_code, order_id),
            )
            active_remaining = cursor.fetchone()["active_count"]

            if active_remaining == 0:
                cursor.execute(
                    "UPDATE equipments SET status = ? WHERE code = ?",
                    (EquipmentStatus.OPERATIONAL.value, wo.equipment_code),
                )

            conn.commit()
            return True

    def cancel_work_order(self, order_id: int) -> bool:
        """Cancels a work order."""
        wo = self.get_work_order_by_id(order_id)
        if not wo:
            return False

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE work_orders SET status = ? WHERE id = ?",
                (WorkOrderStatus.CANCELLED.value, order_id),
            )
            # Check if other active orders exist
            cursor.execute(
                """
                SELECT COUNT(*) as active_count FROM work_orders 
                WHERE equipment_code = ? AND status IN ('PENDING', 'IN_PROGRESS') AND id != ?
                """,
                (wo.equipment_code, order_id),
            )
            if cursor.fetchone()["active_count"] == 0:
                cursor.execute(
                    "UPDATE equipments SET status = ? WHERE code = ?",
                    (EquipmentStatus.OPERATIONAL.value, wo.equipment_code),
                )
            conn.commit()
            return True

    def get_work_orders_for_technician(
        self, technician_name: str, status_filter: Optional[str] = None
    ) -> List[WorkOrder]:
        """
        Returns only work orders assigned specifically to the given technician,
        plus orders that are unassigned / available for anyone ('Sin Asignar', 'Técnico de Turno', etc.).
        Orders assigned to other specific technicians are strictly excluded.
        """
        tech_clean = technician_name.strip()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            unassigned_placeholders = "'', 'Sin Asignar', 'General', 'Disponible', 'Disponibles', 'Técnico de Turno'"

            query_sql = f"""
                SELECT * FROM work_orders 
                WHERE (
                    assigned_technician = ? 
                    OR assigned_technician IS NULL 
                    OR TRIM(assigned_technician) IN ({unassigned_placeholders})
                )
            """
            params: list = [tech_clean]

            if status_filter:
                query_sql += " AND status = ?"
                params.append(status_filter.strip().upper())

            query_sql += " ORDER BY id DESC"
            cursor.execute(query_sql, params)
            rows = cursor.fetchall()

            return [
                WorkOrder(
                    id=r["id"],
                    equipment_code=r["equipment_code"],
                    title=r["title"],
                    description=r["description"] or "",
                    type=r["type"],
                    priority=r["priority"],
                    status=r["status"],
                    assigned_technician=r["assigned_technician"] or "Sin Asignar",
                    downtime_hours=r["downtime_hours"],
                    cost=r["cost"],
                    created_at=r["created_at"],
                    closed_at=r["closed_at"],
                )
                for r in rows
            ]

    def claim_work_order(self, order_id: int, technician_name: str) -> bool:
        """
        Allows a technician to claim an unassigned work order, self-assigning it
        and transitioning it to IN_PROGRESS.
        """
        wo = self.get_work_order_by_id(order_id)
        if not wo:
            return False

        tech_clean = technician_name.strip()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE work_orders 
                SET assigned_technician = ?, status = ?
                WHERE id = ?
                """,
                (tech_clean, WorkOrderStatus.IN_PROGRESS.value, order_id),
            )
            # Update equipment status to MAINTENANCE
            cursor.execute(
                "UPDATE equipments SET status = ? WHERE code = ?",
                (EquipmentStatus.MAINTENANCE.value, wo.equipment_code),
            )
            conn.commit()
            return True

    def load_demo_work_orders(self) -> int:

        """Generates sample work orders for realistic demonstrations."""
        existing = self.get_all_work_orders()
        if existing:
            return 0

        demo_ots = [
            (
                "CMP-001",
                "Cambio de filtros de admisión y aceite",
                "Mantenimiento preventivo rutinario a las 2000 horas.",
                MaintenanceType.PREVENTIVE.value,
                Priority.MEDIUM.value,
                "Ing. Carlos Mendoza",
            ),
            (
                "MTR-305",
                "Sustitución de rodamientos lado acople",
                "Falla por calentamiento excesivo y vibración alta.",
                MaintenanceType.CORRECTIVE.value,
                Priority.HIGH.value,
                "Tec. Laura Ramos",
            ),
            (
                "BMB-102",
                "Inspección de sello mecánico y alineación",
                "Monitoreo predictivo por ligera fuga en carcasa.",
                MaintenanceType.PREDICTIVE.value,
                Priority.LOW.value,
                "Tec. Andrés Silva",
            ),
        ]

        count = 0
        for code, title, desc, otype, prio, tech in demo_ots:
            try:
                wo = self.create_work_order(code, title, desc, otype, prio, tech)
                if count == 1:
                    # Mark the corrective order as completed with downtime and cost to have historical KPIs
                    self.close_work_order(wo.id, downtime_hours=4.5, cost=350.0)
                elif count == 0:
                    # Leave one in progress
                    self.start_work_order(wo.id)
                count += 1
            except Exception:
                continue
        return count
