"""
IoT / Arduino Service: Reads sensor telemetry or simulates industrial sensor streams.
Detects abnormal temperature and vibration spikes (ISO 10816 standards)
and triggers automated predictive maintenance work orders.
"""

from datetime import datetime
import random
from typing import Optional, Tuple
from ..database.db_manager import db_manager
from ..models.entities import (
    EquipmentStatus,
    MaintenanceType,
    Priority,
    TelemetryReading,
)
from .work_order_service import WorkOrderService

# Try importing pyserial optionally
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class IoTService:
    """Handles sensor reading from real Arduino via Serial or realistic simulation."""

    # Industrial threshold limits
    TEMP_WARNING_C = 70.0
    TEMP_CRITICAL_C = 85.0

    VIB_WARNING_MMS = 4.5    # ISO 10816 Group 1/2 warning
    VIB_CRITICAL_MMS = 7.1   # ISO 10816 Group 1/2 critical

    def __init__(self, db=db_manager, wo_service: Optional[WorkOrderService] = None):
        self.db = db
        self.wo_service = wo_service or WorkOrderService(db)

    def is_serial_available(self) -> bool:
        """Returns True if pyserial is installed."""
        return SERIAL_AVAILABLE

    def record_telemetry(
        self, equipment_code: str, temperature: float, vibration: float, current: float
    ) -> TelemetryReading:
        """Saves a telemetry reading into database."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO telemetry_logs (equipment_code, temperature, vibration, current, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (equipment_code, round(temperature, 2), round(vibration, 2), round(current, 2), timestamp),
            )
            rec_id = cursor.lastrowid
            conn.commit()

        return TelemetryReading(
            id=rec_id,
            equipment_code=equipment_code,
            temperature=round(temperature, 2),
            vibration=round(vibration, 2),
            current=round(current, 2),
            timestamp=timestamp,
        )

    def analyze_and_alert(
        self, reading: TelemetryReading
    ) -> Tuple[str, Optional[int]]:
        """
        Evaluates reading against industrial thresholds.
        If thresholds are exceeded, generates an automatic Predictive Work Order.
        Returns (status_severity, created_work_order_id).
        """
        is_critical = (
            reading.temperature >= self.TEMP_CRITICAL_C
            or reading.vibration >= self.VIB_CRITICAL_MMS
        )
        is_warning = (
            reading.temperature >= self.TEMP_WARNING_C
            or reading.vibration >= self.VIB_WARNING_MMS
        )

        if not is_warning and not is_critical:
            return "NORMAL", None

        severity = "CRITICAL" if is_critical else "WARNING"
        prio = Priority.CRITICAL.value if is_critical else Priority.HIGH.value

        title = f"ALERTA PREDICTIVA IoT: Parámetros fuera de rango en {reading.equipment_code}"
        desc = (
            f"Alerta automática generada por telemetría sensorial.\n"
            f"• Temperatura registrada: {reading.temperature}°C (Límite alerta: {self.TEMP_WARNING_C}°C, Crítico: {self.TEMP_CRITICAL_C}°C)\n"
            f"• Vibración RMS: {reading.vibration} mm/s (Límite ISO 10816: {self.VIB_WARNING_MMS} mm/s)\n"
            f"• Corriente consumida: {reading.current} A\n"
            f"Acción recomendada: Inspección inmediata de lubricación, balanceo de rotor y refrigeración."
        )

        # Update equipment status in DB
        new_status = EquipmentStatus.DOWN.value if is_critical else EquipmentStatus.WARNING.value
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE equipments SET status = ? WHERE code = ?",
                (new_status, reading.equipment_code),
            )
            conn.commit()

        # Create automated predictive work order
        wo = self.wo_service.create_work_order(
            equipment_code=reading.equipment_code,
            title=title,
            description=desc,
            order_type=MaintenanceType.PREDICTIVE.value,
            priority=prio,
            assigned_technician="Sistema Automático IoT / Predictivo",
        )

        return severity, wo.id

    def simulate_telemetry_reading(
        self, equipment_code: str, inject_anomaly: bool = False
    ) -> Tuple[TelemetryReading, str, Optional[int]]:
        """
        Generates realistic telemetry for equipment.
        If inject_anomaly=True, introduces critical temperature or vibration spike.
        Returns (reading, severity, created_wo_id).
        """
        if inject_anomaly:
            temp = round(random.uniform(86.0, 98.5), 2)
            vib = round(random.uniform(7.5, 11.2), 2)
            curr = round(random.uniform(28.0, 36.0), 2)
        else:
            # Normal industrial operation
            temp = round(random.uniform(48.0, 68.0), 2)
            vib = round(random.uniform(1.2, 3.8), 2)
            curr = round(random.uniform(14.0, 22.0), 2)

        reading = self.record_telemetry(equipment_code, temp, vib, curr)
        severity, wo_id = self.analyze_and_alert(reading)
        return reading, severity, wo_id

    def read_real_serial_line(self, port: str, baudrate: int = 9600) -> Optional[str]:
        """
        Attempts to read a single line from an actual connected Arduino via Serial.
        Expected line format from Arduino sketch: 'TEMP:65.4,VIB:2.1,CURR:15.2'
        """
        if not SERIAL_AVAILABLE:
            raise RuntimeError(
                "La librería 'pyserial' no está instalada. Ejecute 'pip install pyserial' para conectar hardware real."
            )

        with serial.Serial(port, baudrate, timeout=2.0) as ser:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            return line if line else None
