"""
Industrial Maintenance Management System (CMMS) - HTTP REST API & Web Server.
Built with Python standard library (http.server) - zero external dependencies required.
Supports Local Network & Wi-Fi mobile/tablet access, Technician Portal, and Mobile Notifications.
"""

from dataclasses import asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import socket
import sys
from typing import Any, Dict, Optional
import urllib.parse

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.services.equipment_service import EquipmentService
from src.services.work_order_service import WorkOrderService
from src.services.metrics_service import MetricsService
from src.services.export_service import ExportService
from src.services.iot_service import IoTService
from src.services.notification_service import NotificationService
from src.services.auth_service import AuthService
from src.models.entities import User, UserRole


def get_local_ip() -> str:
    """Detects local LAN IPv4 address (e.g. 192.168.1.50) for mobile/tablet access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class CMMSRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for the CMMS web interface, Technician Portal, and REST API."""

    STATIC_DIR = (BASE_DIR / "public") if (BASE_DIR / "public").exists() else (Path(__file__).resolve().parent / "static")
    REPORTS_DIR = BASE_DIR / "reports"

    # Services singletons per handler instance
    eq_service = EquipmentService()
    wo_service = WorkOrderService()
    metrics_service = MetricsService()
    export_service = ExportService()
    iot_service = IoTService(wo_service=wo_service)
    notification_service = NotificationService()
    auth_service = AuthService()

    def _get_authenticated_user(self) -> Optional[User]:
        """Extracts and verifies Bearer token from Authorization header or query param."""
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):].strip()
        if not token:
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            token = q.get("token", [""])[0].strip()

        if token:
            return self.auth_service.get_user_from_token(token)
        return None

    def log_message(self, format: str, *args: Any) -> None:

        """Customize logging to keep console neat."""
        sys.stderr.write(f"[CMMS-Web] {self.address_string()} - {format % args}\n")

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Helper to send JSON response with UTF-8 encoding."""
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_error(self, message: str, status: int = 400) -> None:
        """Helper to send JSON error response."""
        self._send_json({"error": message, "success": False}, status=status)

    def _read_body_json(self) -> Dict[str, Any]:
        """Parses request body as JSON."""
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        raw = self.rfile.read(content_len).decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _get_request_path_and_query(self):
        """Resolves request path and query parameters supporting both local and Vercel serverless rewrites."""
        raw_path = (
            self.headers.get("x-matched-path")
            or self.headers.get("x-forwarded-uri")
            or self.headers.get("x-invoke-path")
            or self.path
        )
        parsed = urllib.parse.urlparse(raw_path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        # If rewritten to /api/index or /api/index.py, inspect query params (e.g., match or path parameter)
        if path in ("/api/index.py", "/api/index", "/api"):
            candidates = query.get("match", []) or query.get("path", [])
            if candidates:
                sub = candidates[0].lstrip("/")
                path = f"/api/{sub}"

        return path, query

    def do_OPTIONS(self) -> None:
        """Handles preflight requests."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    # =========================================================================
    # STATIC FILES SERVING (INCLUDING MOBILE TECHNICIAN PORTAL)
    # =========================================================================
    def _serve_static_file(self, rel_path: str) -> bool:
        """Serves static files from the static directory."""
        clean_path = rel_path.split("?")[0].rstrip("/")
        if clean_path in ("", "/"):
            target = self.STATIC_DIR / "index.html"
        elif clean_path in ("/tecnico", "/tecnico.html"):
            target = self.STATIC_DIR / "tecnico.html"
        elif clean_path in ("/login", "/login.html"):
            target = self.STATIC_DIR / "login.html"
        else:
            clean_rel = clean_path.lstrip("/\\")
            target = (self.STATIC_DIR / clean_rel).resolve()


        # Prevent directory traversal
        try:
            target.relative_to(self.STATIC_DIR.resolve())
        except ValueError:
            self._send_error("Forbidden path", 403)
            return True

        if not target.exists() or not target.is_file():
            return False

        ext = target.suffix.lower()
        mime_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        mime = mime_types.get(ext, "application/octet-stream")

        with open(target, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(content)
        return True

    # =========================================================================
    # GET DISPATCHER
    # =========================================================================
    def do_GET(self) -> None:
        path, query = self._get_request_path_and_query()

        # 0. API Auth Me
        if path == "/api/auth/me":
            user = self._get_authenticated_user()
            if not user:
                return self._send_error("No autenticado", 401)
            return self._send_json({
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role,
                }
            })

        # 0.1 API Technicians List
        elif path == "/api/users/technicians":
            techs = self.auth_service.get_all_technicians()
            return self._send_json({"success": True, "technicians": techs})

        # 1. API Network Info (for QR Code & Mobile Wi-Fi connection)
        elif path == "/api/network-info":
            local_ip = get_local_ip()
            port = getattr(self.server, "server_address", (None, 5000))[1] if hasattr(self, "server") and self.server else 5000
            return self._send_json({
                "success": True,
                "local_ip": local_ip,
                "port": port,
                "dashboard_url": f"http://{local_ip}:{port}",
                "technician_url": f"http://{local_ip}:{port}/tecnico",
            })

        # 2. API Equipments
        elif path == "/api/equipments":
            search_query = query.get("q", [None])[0]
            if search_query:
                eqs = self.eq_service.search_equipments(search_query)
            else:
                eqs = self.eq_service.get_all_equipments()
            return self._send_json({"success": True, "equipments": [asdict(e) for e in eqs]})

        elif path.startswith("/api/equipments/"):
            code = urllib.parse.unquote(path[len("/api/equipments/"):])
            eq = self.eq_service.get_equipment_by_code(code)
            if not eq:
                return self._send_error(f"Equipo '{code}' no encontrado", 404)
            return self._send_json({"success": True, "equipment": asdict(eq)})

        # 3. API Work Orders (Role-based filtering for Technicians)
        elif path == "/api/work-orders":
            status_filter = query.get("status", [None])[0]
            active_only = query.get("active", ["0"])[0] in ("1", "true")
            tech_param = query.get("technician", [None])[0]
            user = self._get_authenticated_user()

            if tech_param:
                all_ots = self.wo_service.get_work_orders_for_technician(tech_param, status_filter)
            elif user and user.role == UserRole.TECHNICIAN.value:
                # Strictly only assigned orders + unassigned orders
                all_ots = self.wo_service.get_work_orders_for_technician(user.full_name, status_filter)
            else:
                # Admin or unauthenticated tests
                all_ots = self.wo_service.get_all_work_orders(status_filter)

            if active_only:
                all_ots = [o for o in all_ots if o.status in ("PENDING", "IN_PROGRESS")]
            return self._send_json({"success": True, "work_orders": [asdict(o) for o in all_ots]})

        elif path.startswith("/api/work-orders/"):
            subpath = path[len("/api/work-orders/"):].strip("/")
            if subpath.startswith("by-equipment/"):
                eq_code = urllib.parse.unquote(subpath[len("by-equipment/"):])
                ots = self.wo_service.get_work_orders_by_equipment(eq_code)
                return self._send_json({"success": True, "work_orders": [asdict(o) for o in ots]})
            else:
                try:
                    wo_id = int(subpath)
                    wo = self.wo_service.get_work_order_by_id(wo_id)
                    if not wo:
                        return self._send_error(f"Orden de trabajo #{wo_id} no encontrada", 404)
                    return self._send_json({"success": True, "work_order": asdict(wo)})
                except ValueError:
                    return self._send_error("ID de orden inválido", 400)

        # 4. API KPIs
        elif path == "/api/kpis":
            kpis = self.metrics_service.get_plant_kpis()
            return self._send_json({"success": True, "kpis": kpis})

        elif path.startswith("/api/kpis/"):
            code = urllib.parse.unquote(path[len("/api/kpis/"):])
            try:
                eq_kpi = self.metrics_service.get_equipment_kpis(code)
                return self._send_json({"success": True, "kpi": eq_kpi})
            except Exception as e:
                return self._send_error(str(e), 404)

        # 5. API Notifications Config & Status
        elif path == "/api/notifications/config":
            return self._send_json({
                "success": True,
                "config": self.notification_service.get_public_config(),
                "history": self.notification_service.history[:10],
            })

        elif path == "/api/iot/status":
            return self._send_json({
                "success": True,
                "serial_available": self.iot_service.is_serial_available()
            })

        # 6. CSV Download
        elif path.startswith("/api/download/"):
            filename = urllib.parse.unquote(path[len("/api/download/"):])
            safe_filename = Path(filename).name
            file_path = self.REPORTS_DIR / safe_filename
            if not file_path.exists():
                return self._send_error("Archivo no encontrado", 404)

            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{safe_filename}"')
            self.send_header("Content-Length", str(len(content)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
            return

        # Static fallback
        if not self._serve_static_file(path):
            self._send_error("Recurso no encontrado", 404)

    # =========================================================================
    # POST DISPATCHER
    # =========================================================================
    def do_POST(self) -> None:
        path, query = self._get_request_path_and_query()
        body = self._read_body_json()

        # 0. Auth - Login
        if path == "/api/auth/login":
            username = body.get("username", "")
            password = body.get("password", "")
            auth_res = self.auth_service.authenticate(username, password)
            if not auth_res:
                return self._send_error("Usuario o contraseña incorrectos", 401)
            return self._send_json({"success": True, "token": auth_res["token"], "user": auth_res["user"]})

        # 0.1 Auth - Logout
        elif path == "/api/auth/logout":
            return self._send_json({"success": True, "message": "Sesión cerrada correctamente"})

        # 0.2 Auth - Change Password
        elif path == "/api/auth/change-password":
            user = self._get_authenticated_user()
            if not user:
                return self._send_error("Debe iniciar sesión para cambiar la contraseña", 401)
            current_pass = body.get("current_password", "")
            new_pass = body.get("new_password", "")
            if not current_pass or not new_pass:
                return self._send_error("Debe proporcionar la contraseña actual y la nueva", 400)
            try:
                self.auth_service.change_password(user.id, current_pass, new_pass)
                return self._send_json({"success": True, "message": "Contraseña actualizada exitosamente"})
            except ValueError as ve:
                return self._send_error(str(ve), 400)
            except Exception as e:
                return self._send_error(f"Error al cambiar contraseña: {str(e)}", 500)

        # 1. Equipments - Create
        elif path == "/api/equipments":
            code = body.get("code", "")
            name = body.get("name", "")
            eq_type = body.get("type", "General")
            location = body.get("location", "Planta Principal")
            hours = float(body.get("operating_hours", 0.0) or 0.0)

            try:
                eq = self.eq_service.register_equipment(code, name, eq_type, location, hours)
                return self._send_json({"success": True, "equipment": asdict(eq)}, status=201)
            except Exception as e:
                return self._send_error(str(e), 400)

        # 2. Work Orders - Create (with Mobile Notification)
        elif path == "/api/work-orders":
            eq_code = body.get("equipment_code", "")
            title = body.get("title", "")
            desc = body.get("description", "")
            order_type = body.get("type", "PREVENTIVE")
            priority = body.get("priority", "MEDIUM")
            tech = body.get("assigned_technician", "Técnico de Turno")

            try:
                wo = self.wo_service.create_work_order(
                    equipment_code=eq_code,
                    title=title,
                    description=desc,
                    order_type=order_type,
                    priority=priority,
                    assigned_technician=tech,
                )

                # Automatic Mobile Alert Dispatch
                local_ip = get_local_ip()
                port = getattr(self.server, "server_address", (None, 5000))[1] if hasattr(self, "server") and self.server else 5000
                direct_link = f"http://{local_ip}:{port}/tecnico?id={wo.id}"
                alert_log = self.notification_service.send_work_order_alert(wo, direct_url=direct_link)

                return self._send_json({
                    "success": True,
                    "work_order": asdict(wo),
                    "notification": alert_log,
                }, status=201)
            except Exception as e:
                return self._send_error(str(e), 400)

        # 2.1 Work Orders - Claim (Self-assign to Technician)
        elif path.endswith("/claim") and path.startswith("/api/work-orders/"):
            try:
                wo_id = int(path.split("/")[3])
                user = self._get_authenticated_user()
                tech_name = body.get("technician_name")
                if not tech_name:
                    if user:
                        tech_name = user.full_name
                    else:
                        return self._send_error("Debe especificar el técnico o iniciar sesión", 401)

                if self.wo_service.claim_work_order(wo_id, tech_name):
                    return self._send_json({
                        "success": True,
                        "message": f"OT #{wo_id} tomada exitosamente por {tech_name}",
                    })
                return self._send_error(f"No se pudo tomar la OT #{wo_id}", 400)
            except Exception as e:
                return self._send_error(str(e), 400)

        # 3. Work Orders - Start
        elif path.endswith("/start") and path.startswith("/api/work-orders/"):
            try:
                wo_id = int(path.split("/")[3])
                if self.wo_service.start_work_order(wo_id):
                    return self._send_json({"success": True, "message": f"OT #{wo_id} iniciada"})
                return self._send_error("No se pudo iniciar la OT", 400)
            except Exception as e:
                return self._send_error(str(e), 400)

        # 4. Work Orders - Finish (with Technician Report: Work Done & Materials Used)
        elif (path.endswith("/finish") or path.endswith("/close")) and path.startswith("/api/work-orders/"):
            try:
                wo_id = int(path.split("/")[3])
                downtime = float(body.get("downtime_hours", 0.0) or 0.0)
                cost = float(body.get("cost", 0.0) or 0.0)
                work_done = body.get("work_done", "")
                materials_used = body.get("materials_used", "")

                if self.wo_service.close_work_order(
                    wo_id,
                    downtime_hours=downtime,
                    cost=cost,
                    work_done=work_done,
                    materials_used=materials_used,
                ):
                    return self._send_json({
                        "success": True,
                        "message": f"OT #{wo_id} liquidada y finalizada correctamente.",
                    })
                return self._send_error("No se pudo finalizar la OT", 400)
            except Exception as e:
                return self._send_error(str(e), 400)

        # 5. Work Orders - Cancel
        elif path.endswith("/cancel") and path.startswith("/api/work-orders/"):
            try:
                wo_id = int(path.split("/")[3])
                if self.wo_service.cancel_work_order(wo_id):
                    return self._send_json({"success": True, "message": f"OT #{wo_id} cancelada"})
                return self._send_error("No se pudo cancelar la OT", 400)
            except Exception as e:
                return self._send_error(str(e), 400)

        # 6. Notifications - Configuration Update & Test
        elif path == "/api/notifications/config":
            try:
                self.notification_service.save_config(body)
                return self._send_json({"success": True, "message": "Configuración de notificaciones guardada."})
            except Exception as e:
                return self._send_error(str(e), 400)

        elif path == "/api/notifications/test":
            local_ip = get_local_ip()
            port = self.server.server_address[1]
            test_url = f"http://{local_ip}:{port}/tecnico"
            res = self.notification_service.send_test_notification(test_url=test_url)
            return self._send_json(res)

        # 7. CSV Export
        elif path == "/api/export":
            try:
                eq_file, wo_file = self.export_service.export_all_to_csv()
                eq_name = Path(eq_file).name
                wo_name = Path(wo_file).name
                return self._send_json({
                    "success": True,
                    "equipments_file": eq_name,
                    "work_orders_file": wo_name,
                    "equipments_url": f"/api/download/{eq_name}",
                    "work_orders_url": f"/api/download/{wo_name}",
                })
            except Exception as e:
                return self._send_error(f"Error exportando reportes: {str(e)}", 500)

        # 8. IoT Simulation (with Automatic Mobile Alert on critical condition)
        elif path == "/api/iot/simulate":
            code = body.get("equipment_code", "")
            inject = bool(body.get("inject_anomaly", False))
            if not code:
                eqs = self.eq_service.get_all_equipments()
                if not eqs:
                    return self._send_error("No hay equipos registrados para censar.", 400)
                code = eqs[0].code

            try:
                reading, severity, wo_id = self.iot_service.simulate_telemetry_reading(
                    code, inject_anomaly=inject
                )

                if wo_id:
                    wo = self.wo_service.get_work_order_by_id(wo_id)
                    if wo:
                        local_ip = get_local_ip()
                        port = self.server.server_address[1]
                        self.notification_service.send_work_order_alert(
                            wo, direct_url=f"http://{local_ip}:{port}/tecnico?id={wo.id}"
                        )

                return self._send_json({
                    "success": True,
                    "reading": asdict(reading),
                    "severity": severity,
                    "work_order_id": wo_id,
                })
            except Exception as e:
                return self._send_error(str(e), 400)

        # 9. IoT Serial Read (Physical Arduino)
        elif path == "/api/iot/serial":
            port = body.get("port", "COM3")
            try:
                data = self.iot_service.read_real_serial_line(port)
                return self._send_json({"success": True, "data": data})
            except Exception as e:
                return self._send_error(str(e), 400)

        # 10. Load Demo Data
        elif path == "/api/demo":
            eq_count = self.eq_service.load_demo_data()
            wo_count = self.wo_service.load_demo_work_orders()
            return self._send_json({
                "success": True,
                "equipments_loaded": eq_count,
                "work_orders_loaded": wo_count,
                "message": f"Datos cargados: {eq_count} equipos y {wo_count} órdenes de trabajo.",
            })

        self._send_error("Endpoint no encontrado", 404)

    # =========================================================================
    # PUT DISPATCHER (Updates)
    # =========================================================================
    def do_PUT(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_body_json()

        if path.startswith("/api/equipments/"):
            code = urllib.parse.unquote(path[len("/api/equipments/"):])
            hours = float(body["operating_hours"]) if "operating_hours" in body and body["operating_hours"] is not None else None
            success = self.eq_service.update_equipment(
                code=code,
                name=body.get("name"),
                eq_type=body.get("type"),
                location=body.get("location"),
                status=body.get("status"),
                operating_hours=hours,
            )
            if success:
                updated_eq = self.eq_service.get_equipment_by_code(code)
                return self._send_json({"success": True, "equipment": asdict(updated_eq)})
            return self._send_error(f"No se pudo actualizar el equipo '{code}'", 400)

        self._send_error("Endpoint no encontrado", 404)

    # =========================================================================
    # DELETE DISPATCHER
    # =========================================================================
    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/api/equipments/"):
            code = urllib.parse.unquote(path[len("/api/equipments/"):])
            if self.eq_service.delete_equipment(code):
                return self._send_json({"success": True, "message": f"Equipo '{code}' eliminado"})
            return self._send_error(f"No se pudo eliminar el equipo '{code}'", 400)

        self._send_error("Endpoint no encontrado", 404)


def create_server(host: str = "0.0.0.0", port: int = 5000) -> HTTPServer:
    """Creates configured HTTP server instance listening on all network interfaces."""
    server = HTTPServer((host, port), CMMSRequestHandler)
    return server
