"""
Equipment Service: Business logic for managing plant assets and equipment.
"""

from datetime import datetime
from typing import List, Optional
from ..database.db_manager import db_manager
from ..models.entities import Equipment, EquipmentStatus


class EquipmentService:
    """Provides CRUD operations and business logic for Equipment assets."""

    def __init__(self, db=db_manager):
        self.db = db

    def register_equipment(
        self,
        code: str,
        name: str,
        eq_type: str,
        location: str,
        operating_hours: float = 0.0,
    ) -> Equipment:
        """
        Registers a new equipment asset in the database.
        Raises ValueError if required fields are missing or code already exists.
        """
        code = code.strip().upper()
        name = name.strip()
        eq_type = eq_type.strip() if eq_type else "General"
        location = location.strip() if location else "Planta Principal"

        if not code or not name:
            raise ValueError("El código y el nombre del equipo son obligatorios.")

        if self.get_equipment_by_code(code) is not None:
            raise ValueError(f"Ya existe un equipo registrado con el código '{code}'.")

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = EquipmentStatus.OPERATIONAL.value

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO equipments (code, name, type, location, status, operating_hours, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (code, name, eq_type, location, status, float(operating_hours), created_at),
            )
            conn.commit()

        return Equipment(
            code=code,
            name=name,
            type=eq_type,
            location=location,
            status=status,
            operating_hours=float(operating_hours),
            created_at=created_at,
        )

    def get_all_equipments(self) -> List[Equipment]:
        """Returns all registered equipment sorted by code."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM equipments ORDER BY code ASC")
            rows = cursor.fetchall()
            return [
                Equipment(
                    code=r["code"],
                    name=r["name"],
                    type=r["type"],
                    location=r["location"],
                    status=r["status"],
                    operating_hours=r["operating_hours"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def get_equipment_by_code(self, code: str) -> Optional[Equipment]:
        """Retrieves a single equipment by its unique code."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM equipments WHERE code = ?", (code.strip().upper(),))
            row = cursor.fetchone()
            if row:
                return Equipment(
                    code=row["code"],
                    name=row["name"],
                    type=row["type"],
                    location=row["location"],
                    status=row["status"],
                    operating_hours=row["operating_hours"],
                    created_at=row["created_at"],
                )
            return None

    def search_equipments(self, query: str) -> List[Equipment]:
        """Searches equipment by code, name, type, or location."""
        term = f"%{query.strip().lower()}%"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM equipments 
                WHERE LOWER(code) LIKE ? 
                   OR LOWER(name) LIKE ? 
                   OR LOWER(type) LIKE ? 
                   OR LOWER(location) LIKE ?
                ORDER BY code ASC
                """,
                (term, term, term, term),
            )
            rows = cursor.fetchall()
            return [
                Equipment(
                    code=r["code"],
                    name=r["name"],
                    type=r["type"],
                    location=r["location"],
                    status=r["status"],
                    operating_hours=r["operating_hours"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def update_equipment(
        self,
        code: str,
        name: Optional[str] = None,
        eq_type: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        operating_hours: Optional[float] = None,
    ) -> bool:
        """Updates specific fields for an existing equipment asset."""
        eq = self.get_equipment_by_code(code)
        if not eq:
            return False

        updated_name = name.strip() if name is not None and name.strip() else eq.name
        updated_type = eq_type.strip() if eq_type is not None and eq_type.strip() else eq.type
        updated_loc = location.strip() if location is not None and location.strip() else eq.location
        updated_status = status.strip().upper() if status is not None and status.strip() else eq.status
        updated_hours = float(operating_hours) if operating_hours is not None else eq.operating_hours

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE equipments 
                SET name = ?, type = ?, location = ?, status = ?, operating_hours = ?
                WHERE code = ?
                """,
                (updated_name, updated_type, updated_loc, updated_status, updated_hours, code.strip().upper()),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_equipment(self, code: str) -> bool:
        """Deletes an equipment asset by its code (cascades to related work orders)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM equipments WHERE code = ?", (code.strip().upper(),))
            conn.commit()
            return cursor.rowcount > 0

    def load_demo_data(self) -> int:
        """Populates database with realistic industrial equipment if empty."""
        demo_assets = [
            ("CMP-001", "Compresor Tornillo GA-75", "Neumático", "Sala de Compresores", 1850.0),
            ("BMB-102", "Bomba Centrífuga Multietapa", "Hidráulico", "Línea de Enfriamiento", 3420.5),
            ("MTR-305", "Motor Eléctrico Trifásico 75HP", "Eléctrico", "Molino Principal #1", 5210.0),
            ("CNV-040", "Cinta Transportadora Mod-B", "Mecánico", "Área de Empaque", 980.0),
            ("CAL-201", "Caldera Acuotubular 500BHP", "Térmico", "Planta de Vapor", 4120.0),
        ]

        count = 0
        for code, name, eq_type, loc, hours in demo_assets:
            if not self.get_equipment_by_code(code):
                self.register_equipment(code, name, eq_type, loc, hours)
                count += 1
        return count
