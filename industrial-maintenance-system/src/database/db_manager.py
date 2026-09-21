"""
Database Manager for Industrial CMMS using SQLite.
Handles connection, schema initialization, and transactional queries.
"""

from contextlib import contextmanager
import os
import sqlite3
from pathlib import Path
from typing import Generator, Optional


class DatabaseManager:
    """Manages SQLite database connection, tables initialization and queries."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Check for Vercel / Serverless environment (read-only filesystem)
            if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                tmp_dir = Path("/tmp")
                tmp_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = str(tmp_dir / "cmms.db")
                # If bundled data/cmms.db exists, copy it to /tmp if not already there
                base_dir = Path(__file__).resolve().parent.parent.parent
                bundled_db = base_dir / "data" / "cmms.db"
                if bundled_db.exists() and not Path(self.db_path).exists():
                    import shutil
                    try:
                        shutil.copyfile(str(bundled_db), self.db_path)
                    except Exception:
                        pass
            else:
                # Default to <project_root>/data/cmms.db
                base_dir = Path(__file__).resolve().parent.parent.parent
                data_dir = base_dir / "data"
                data_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = str(data_dir / "cmms.db")
        else:
            self.db_path = db_path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        if not (self.db_path and "test_" in Path(self.db_path).name):
            try:
                self.seed_demo_data()
            except Exception:
                pass

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an auto-closing SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initializes tables if they do not already exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Equipments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equipments (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'OPERATIONAL',
                    operating_hours REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL
                );
            """)

            # 2. Work Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_code TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    assigned_technician TEXT,
                    downtime_hours REAL DEFAULT 0.0,
                    cost REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    closed_at TEXT,
                    FOREIGN KEY (equipment_code) REFERENCES equipments (code) ON DELETE CASCADE
                );
            """)

            # 3. Telemetry Logs table (Arduino / IoT)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_code TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    vibration REAL NOT NULL,
                    current REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (equipment_code) REFERENCES equipments (code) ON DELETE CASCADE
                );
            """)

            # 4. Users table (RBAC: ADMIN vs TECHNICIAN)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'TECHNICIAN')),
                    created_at TEXT NOT NULL
                );
            """)

            conn.commit()

    def seed_demo_data(self) -> None:
        """Seeds 8 industrial demo equipments, work orders for each technician and unassigned, and telemetry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Check if equipments already seeded
            cursor.execute("SELECT COUNT(*) as count FROM equipments")
            eq_count = cursor.fetchone()["count"]
            if eq_count < 8:
                equipments = [
                    ("CMP-001", "Compresor Tornillo Rotativo GA-75", "Neumático / Aire", "Sala de Compresores - Nave A", "MAINTENANCE", 1850.5, "2026-09-14 08:00:00"),
                    ("BMB-102", "Bomba Centrífuga Multietapa KSB-80", "Hidráulico / Bombeo", "Línea de Enfriamiento Principal", "MAINTENANCE", 3420.0, "2026-09-14 08:00:00"),
                    ("MTR-305", "Motor Eléctrico Trifásico Siemens 75HP", "Eléctrico / Potencia", "Molino Principal #1", "MAINTENANCE", 5210.0, "2026-09-14 08:00:00"),
                    ("CNV-040", "Banda Transportadora Modular Mod-B", "Mecánico / Transporte", "Área de Empaque y Paletizado", "OPERATIONAL", 980.5, "2026-09-14 08:00:00"),
                    ("CAL-201", "Caldera Pirotubular de Vapor 500BHP", "Térmico / Vapor", "Planta de Servicios Térmicos", "WARNING", 4120.0, "2026-09-14 08:00:00"),
                    ("EXT-501", "Extrusora Industrial Doble Husillo 120mm", "Mecánico / Plásticos", "Nave de Extrusión #3", "OPERATIONAL", 2145.0, "2026-09-14 08:00:00"),
                    ("TOR-108", "Torre de Enfriamiento Tiro Inducido 350TR", "Refrigeración / Térmico", "Patio de Servicios Exteriores", "OPERATIONAL", 3890.0, "2026-09-14 08:00:00"),
                    ("GEN-602", "Generador Diésel de Emergencia Cummins 450kVA", "Generación Eléctrica", "Subestación Eléctrica #2", "OPERATIONAL", 620.0, "2026-09-14 08:00:00"),
                ]
                for code, name, eq_type, loc, status, hours, dt in equipments:
                    cursor.execute("""
                        INSERT OR REPLACE INTO equipments (code, name, type, location, status, operating_hours, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (code, name, eq_type, loc, status, hours, dt))

            # 2. Check work orders count
            cursor.execute("SELECT COUNT(*) as count FROM work_orders")
            wo_count = cursor.fetchone()["count"]
            if wo_count < 12:
                orders = [
                    # Carlos Mendoza (Mecánico)
                    (
                        "CMP-001",
                        "Mantenimiento Preventivo 2000h: Filtros y Aceite Sintético",
                        "Cambio de cartucho separador de aceite, filtro de aire y sustitución de 20L de lubricante sintético ISO VG 46.",
                        "PREVENTIVE", "HIGH", "IN_PROGRESS", "Ing. Carlos Mendoza",
                        0.0, 0.0, "2026-09-18 09:00:00", None
                    ),
                    (
                        "CNV-040",
                        "Ajuste de tensión y alineación de banda transportadora",
                        "Se detecta leve desalineación lateral en el rodillo tensor de cola provocando fricción en el chasis.",
                        "CORRECTIVE", "MEDIUM", "PENDING", "Ing. Carlos Mendoza",
                        0.0, 0.0, "2026-09-19 11:30:00", None
                    ),
                    (
                        "EXT-501",
                        "Inspección Termográfica en Resistencias y Reductor",
                        "Termografía infrarroja de zonas 1 a 6 y medición de temperatura en cojinetes de empuje.\n\n--- INFORME DE CIERRE TÉCNICO ---\n• Trabajo Realizado: Termografía completada. Zona 3 presentaba conexión floja en bornera; se retorqueó a 4.5 Nm. Temperaturas normalizadas en 62°C.\n• Materiales/Repuestos Usados: Grasa para alta temperatura Polyrex EM, terminales de compresión de cobre calibre 8 AWG.",
                        "PREDICTIVE", "MEDIUM", "COMPLETED", "Ing. Carlos Mendoza",
                        1.5, 280.0, "2026-09-17 08:00:00", "2026-09-17 12:30:00"
                    ),

                    # Laura Ramos (Eléctrico)
                    (
                        "GEN-602",
                        "Prueba en Vacío y Verificación de Baterías de Arranque",
                        "Comprobación de electrolito, tensión en flotación (27.4V DC), limpieza de bornes y arranque de prueba 15 min.",
                        "PREVENTIVE", "LOW", "PENDING", "Tec. Laura Ramos",
                        0.0, 0.0, "2026-09-19 14:00:00", None
                    ),
                    (
                        "MTR-305",
                        "Corrección de Sobrecorriente y Reemplazo de Contactor",
                        "El contactor de línea principal presenta arqueo en polos 1 y 3 provocando disparo térmico intermitente.",
                        "CORRECTIVE", "HIGH", "IN_PROGRESS", "Tec. Laura Ramos",
                        0.0, 0.0, "2026-09-18 10:15:00", None
                    ),
                    (
                        "MTR-305",
                        "Medición de Resistencia de Aislamiento (Megóhmetro)",
                        "Ensayo dieléctrico a 1000V DC entre fases y masa para certificar estado de bobinado.\n\n--- INFORME DE CIERRE TÉCNICO ---\n• Trabajo Realizado: Lectura de aislamiento > 850 Megaohms, índice de polarización 2.8 (óptimo). Se cambiaron empaques de la caja de conexiones.\n• Materiales/Repuestos Usados: Empaque de neopreno para caja de borneras, spray limpiador dieléctrico CRC.",
                        "PREDICTIVE", "MEDIUM", "COMPLETED", "Tec. Laura Ramos",
                        2.0, 420.0, "2026-09-16 13:00:00", "2026-09-16 16:30:00"
                    ),

                    # Andrés Silva (Predictivo / Instrumentación)
                    (
                        "CAL-201",
                        "Purga de Fondo y Calibración de Presostatos",
                        "Maniobra de purga de lodos en caldera, control de nivel McDonnell Miller y test de disparo por sobrepresión.",
                        "PREVENTIVE", "HIGH", "PENDING", "Tec. Andrés Silva",
                        0.0, 0.0, "2026-09-19 07:30:00", None
                    ),
                    (
                        "BMB-102",
                        "Reemplazo de Sello Mecánico de Cartucho por Goteo",
                        "Goteo continuo de 15 gotas/min en prensaestopas lado bomba; desmontaje y montaje de nuevo sello de carburo de silicio.",
                        "CORRECTIVE", "CRITICAL", "IN_PROGRESS", "Tec. Andrés Silva",
                        0.0, 0.0, "2026-09-18 15:45:00", None
                    ),
                    (
                        "TOR-108",
                        "Análisis de Vibraciones FFT en Ventilador de Tiro",
                        "Registro espectral en 1X y 2X RPM para diagnosticar posible desbalance o soltura mecánica en aspas.\n\n--- INFORME DE CIERRE TÉCNICO ---\n• Trabajo Realizado: Se detectó incrustación de sarro en 2 aspas que causaba desbalance. Se limpiaron aspas con hidrolavadora y vibración bajó de 4.8 mm/s a 1.2 mm/s RMS (Zona A ISO 10816).\n• Materiales/Repuestos Usados: Desincrustante biodegradable industrial, arandelas de presión de acero inoxidable 316.",
                        "PREDICTIVE", "MEDIUM", "COMPLETED", "Tec. Andrés Silva",
                        1.0, 180.0, "2026-09-15 10:00:00", "2026-09-15 13:00:00"
                    ),

                    # Órdenes SIN ASIGNAR (Disponibles para cualquier técnico)
                    (
                        "EXT-501",
                        "Lubricación de Crapodina y Engranajes Planetarios",
                        "Engrase general con bomba neumática en los puntos de engrase centralizados del cabezal extrusor.",
                        "PREVENTIVE", "MEDIUM", "PENDING", "Sin Asignar",
                        0.0, 0.0, "2026-09-20 08:30:00", None
                    ),
                    (
                        "CAL-201",
                        "Fuga de Vapor en Brida de Válvula de Seguridad #2",
                        "Vapor visible en junta espirometálica. Requiere despresurizar línea secundaria y cambio de empaque.",
                        "CORRECTIVE", "CRITICAL", "PENDING", "Sin Asignar",
                        0.0, 0.0, "2026-09-20 10:15:00", None
                    ),
                    (
                        "CMP-001",
                        "Monitoreo Acústico de Ultrasonido en Red de Aire",
                        "Rastreo con detector de ultrasonido digital en colectores de 4 pulgadas y derivaciones a naves B y C.",
                        "PREDICTIVE", "LOW", "PENDING", "Sin Asignar",
                        0.0, 0.0, "2026-09-20 13:45:00", None
                    ),
                    (
                        "TOR-108",
                        "Sustitución de Sensor de Flujo y Válvula Solenoide",
                        "La válvula solenoide de reposición de agua tratada no cierra herméticamente provocando desborde leve en balsa.",
                        "CORRECTIVE", "HIGH", "PENDING", "Sin Asignar",
                        0.0, 0.0, "2026-09-21 09:00:00", None
                    ),
                ]

                for eq_c, tit, des, typ, prio, st, tech, down, cst, c_at, cl_at in orders:
                    cursor.execute("""
                        INSERT INTO work_orders (
                            equipment_code, title, description, type, priority, status,
                            assigned_technician, downtime_hours, cost, created_at, closed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (eq_c, tit, des, typ, prio, st, tech, down, cst, c_at, cl_at))

            # 3. Telemetry Logs (IoT readings)
            cursor.execute("SELECT COUNT(*) as count FROM telemetry_logs")
            tel_count = cursor.fetchone()["count"]
            if tel_count < 10:
                readings = [
                    ("CMP-001", 76.5, 2.4, 42.1, "2026-09-21 11:00:00"),
                    ("CMP-001", 78.2, 2.8, 43.5, "2026-09-21 12:00:00"),
                    ("MTR-305", 58.0, 1.6, 68.2, "2026-09-21 11:00:00"),
                    ("MTR-305", 61.2, 1.9, 71.0, "2026-09-21 12:00:00"),
                    ("BMB-102", 44.5, 3.8, 28.4, "2026-09-21 11:00:00"),
                    ("BMB-102", 46.0, 4.2, 29.1, "2026-09-21 12:00:00"),
                    ("EXT-501", 62.0, 1.4, 85.0, "2026-09-21 11:00:00"),
                    ("TOR-108", 32.5, 1.2, 18.0, "2026-09-21 11:00:00"),
                ]
                for eq_c, temp, vib, cur, ts in readings:
                    cursor.execute("""
                        INSERT INTO telemetry_logs (equipment_code, temperature, vibration, current, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (eq_c, temp, vib, cur, ts))

            conn.commit()


# Singleton / Global instance default
db_manager = DatabaseManager()

