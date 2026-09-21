"""
Metrics Service: Calculates industrial maintenance KPIs (MTBF, MTTR, Availability, Costs).
"""

from typing import Any, Dict
from ..database.db_manager import db_manager


class MetricsService:
    """Calculates plant-wide and asset-specific maintenance indicators."""

    def __init__(self, db=db_manager):
        self.db = db

    def get_plant_kpis(self) -> Dict[str, Any]:
        """
        Computes overall plant metrics:
        - Total assets and status distribution
        - Work orders distribution
        - MTBF (Mean Time Between Failures)
        - MTTR (Mean Time To Repair)
        - Plant Operational Availability (%)
        - Total Maintenance Expenditure
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Equipments summary
            cursor.execute("SELECT status, COUNT(*) as count FROM equipments GROUP BY status")
            status_rows = cursor.fetchall()
            status_dist = {r["status"]: r["count"] for r in status_rows}
            total_equipments = sum(status_dist.values())

            # Total operating hours
            cursor.execute("SELECT SUM(operating_hours) as total_hours FROM equipments")
            res_hours = cursor.fetchone()
            total_operating_hours = res_hours["total_hours"] if res_hours and res_hours["total_hours"] else 0.0

            # 2. Work Orders summary
            cursor.execute("SELECT status, COUNT(*) as count FROM work_orders GROUP BY status")
            wo_rows = cursor.fetchall()
            wo_dist = {r["status"]: r["count"] for r in wo_rows}
            total_work_orders = sum(wo_dist.values())

            # 3. Corrective Maintenance Failures & Downtime
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as failure_count,
                    SUM(downtime_hours) as total_downtime,
                    SUM(cost) as total_cost
                FROM work_orders 
                WHERE type = 'CORRECTIVE' AND status = 'COMPLETED'
                """
            )
            corr_row = cursor.fetchone()
            corrective_failures = corr_row["failure_count"] if corr_row else 0
            corrective_downtime = corr_row["total_downtime"] or 0.0 if corr_row else 0.0

            # Total Cost across all completed work orders
            cursor.execute("SELECT SUM(cost) as total_cost FROM work_orders WHERE status = 'COMPLETED'")
            cost_row = cursor.fetchone()
            total_cost = cost_row["total_cost"] or 0.0 if cost_row else 0.0

            # 4. KPI Calculations
            # MTBF = Operating Hours / Number of Corrective Failures
            if corrective_failures > 0:
                mtbf = total_operating_hours / corrective_failures
                mttr = corrective_downtime / corrective_failures
                availability = (mtbf / (mtbf + mttr)) * 100.0 if (mtbf + mttr) > 0 else 100.0
            else:
                mtbf = total_operating_hours
                mttr = 0.0
                availability = 100.0 if total_operating_hours > 0 else 100.0

            return {
                "total_equipments": total_equipments,
                "status_distribution": status_dist,
                "total_operating_hours": round(total_operating_hours, 1),
                "total_work_orders": total_work_orders,
                "active_work_orders": wo_dist.get("PENDING", 0) + wo_dist.get("IN_PROGRESS", 0),
                "completed_work_orders": wo_dist.get("COMPLETED", 0),
                "corrective_failures": corrective_failures,
                "corrective_downtime_hours": round(corrective_downtime, 2),
                "total_cost": round(total_cost, 2),
                "mtbf_hours": round(mtbf, 1) if corrective_failures > 0 else "N/A (0 fallas)",
                "mttr_hours": round(mttr, 2) if corrective_failures > 0 else "0.0 h",
                "availability_pct": round(min(100.0, max(0.0, availability)), 2),
            }

    def get_equipment_kpis(self, equipment_code: str) -> Dict[str, Any]:
        """Computes KPIs specific to a single equipment."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM equipments WHERE code = ?", (equipment_code.strip().upper(),))
            eq = cursor.fetchone()
            if not eq:
                raise ValueError(f"Equipo '{equipment_code}' no encontrado.")

            op_hours = eq["operating_hours"] or 0.0

            cursor.execute(
                """
                SELECT 
                    COUNT(*) as fail_count,
                    SUM(downtime_hours) as downtime,
                    SUM(cost) as cost
                FROM work_orders
                WHERE equipment_code = ? AND type = 'CORRECTIVE' AND status = 'COMPLETED'
                """,
                (eq["code"],),
            )
            corr = cursor.fetchone()
            fails = corr["fail_count"] if corr else 0
            downtime = corr["downtime"] or 0.0 if corr else 0.0
            cost = corr["cost"] or 0.0 if corr else 0.0

            if fails > 0:
                mtbf = op_hours / fails
                mttr = downtime / fails
                avail = (mtbf / (mtbf + mttr)) * 100.0 if (mtbf + mttr) > 0 else 100.0
            else:
                mtbf = op_hours
                mttr = 0.0
                avail = 100.0

            return {
                "code": eq["code"],
                "name": eq["name"],
                "status": eq["status"],
                "operating_hours": op_hours,
                "corrective_failures": fails,
                "downtime_hours": round(downtime, 2),
                "total_cost": round(cost, 2),
                "mtbf": round(mtbf, 1) if fails > 0 else "N/A (0 fallas)",
                "mttr": round(mttr, 2) if fails > 0 else "0.0 h",
                "availability": round(min(100.0, max(0.0, avail)), 2),
            }
