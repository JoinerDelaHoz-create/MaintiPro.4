"""
Export Service: Exports equipment inventory and maintenance history to CSV.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Tuple
from ..database.db_manager import db_manager


class ExportService:
    """Exports system data to CSV format for analysis in Excel or BI tools."""

    def __init__(self, db=db_manager):
        self.db = db
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.reports_dir = base_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def export_all_to_csv(self) -> Tuple[str, str]:
        """
        Exports both equipment and work orders tables to separate timestamped CSV files.
        Returns paths to the generated files.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        eq_file = self.reports_dir / f"equipos_{timestamp}.csv"
        wo_file = self.reports_dir / f"ordenes_trabajo_{timestamp}.csv"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Export Equipments
            cursor.execute("SELECT * FROM equipments ORDER BY code ASC")
            eq_rows = cursor.fetchall()
            with open(eq_file, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Codigo", "Nombre", "Tipo", "Ubicacion", "Estado", "Horas_Operacion", "Fecha_Registro"])
                for r in eq_rows:
                    writer.writerow([
                        r["code"],
                        r["name"],
                        r["type"],
                        r["location"],
                        r["status"],
                        r["operating_hours"],
                        r["created_at"],
                    ])

            # 2. Export Work Orders
            cursor.execute("SELECT * FROM work_orders ORDER BY id DESC")
            wo_rows = cursor.fetchall()
            with open(wo_file, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID",
                    "Codigo_Equipo",
                    "Titulo",
                    "Descripcion",
                    "Tipo",
                    "Prioridad",
                    "Estado",
                    "Tecnico_Asignado",
                    "Horas_Paro",
                    "Costo_USD",
                    "Fecha_Creacion",
                    "Fecha_Cierre",
                ])
                for r in wo_rows:
                    writer.writerow([
                        r["id"],
                        r["equipment_code"],
                        r["title"],
                        r["description"],
                        r["type"],
                        r["priority"],
                        r["status"],
                        r["assigned_technician"],
                        r["downtime_hours"],
                        r["cost"],
                        r["created_at"],
                        r["closed_at"] or "N/A",
                    ])

        return str(eq_file), str(wo_file)
