"""
Industrial Maintenance Management System (CMMS) - Domain Models
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EquipmentStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    DOWN = "DOWN"
    WARNING = "WARNING"


class MaintenanceType(str, Enum):
    PREVENTIVE = "PREVENTIVE"
    CORRECTIVE = "CORRECTIVE"
    PREDICTIVE = "PREDICTIVE"


class WorkOrderStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Equipment:
    code: str
    name: str
    type: str
    location: str
    status: str = EquipmentStatus.OPERATIONAL.value
    operating_hours: float = 0.0
    created_at: Optional[str] = None


@dataclass
class WorkOrder:
    id: Optional[int]
    equipment_code: str
    title: str
    description: str
    type: str
    priority: str
    status: str
    assigned_technician: str
    downtime_hours: float = 0.0
    cost: float = 0.0
    created_at: Optional[str] = None
    closed_at: Optional[str] = None


@dataclass
class TelemetryReading:
    id: Optional[int]
    equipment_code: str
    temperature: float
    vibration: float
    current: float
    timestamp: Optional[str] = None


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    TECHNICIAN = "TECHNICIAN"


@dataclass
class User:
    id: Optional[int]
    username: str
    password_hash: str
    salt: str
    full_name: str
    role: str = UserRole.TECHNICIAN.value
    created_at: Optional[str] = None

