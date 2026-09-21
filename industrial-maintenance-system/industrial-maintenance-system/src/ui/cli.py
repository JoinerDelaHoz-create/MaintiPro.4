"""
Interactive Terminal UI for Industrial Maintenance Management System (CMMS).
"""

import os
import sys
from typing import Optional

from .colors import (
    BG_BLUE,
    BG_RED,
    BG_YELLOW,
    BOLD,
    CYAN,
    GRAY,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    WHITE,
    YELLOW,
    colorize_status,
)
from .table_formatter import truncate
from ..models.entities import MaintenanceType, Priority
from ..services.equipment_service import EquipmentService
from ..services.export_service import ExportService
from ..services.iot_service import IoTService
from ..services.metrics_service import MetricsService
from ..services.work_order_service import WorkOrderService


class CMMSApp:
    """Main CLI Application controller."""

    def __init__(self):
        self.eq_service = EquipmentService()
        self.wo_service = WorkOrderService()
        self.metrics_service = MetricsService()
        self.export_service = ExportService()
        self.iot_service = IoTService(wo_service=self.wo_service)

    @staticmethod
    def clear():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def pause():
        input(f"\n{GRAY}Presione [Enter] para continuar...{RESET}")

    def header(self, subtitle: str = "Asset & Maintenance Operations"):
        print(f"{CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}║{RESET}  {BOLD}SISTEMA DE GESTIÓN DE MANTENIMIENTO INDUSTRIAL (CMMS){RESET}                {CYAN}║{RESET}")
        print(f"{CYAN}║{RESET}  {GRAY}{truncate(subtitle, 65):<65}{RESET}  {CYAN}║{RESET}")
        print(f"{CYAN}╚═══════════════════════════════════════════════════════════════════════════════╝{RESET}")

    # =========================================================================
    # 1. GESTIÓN DE EQUIPOS
    # =========================================================================
    def menu_equipment(self):
        while True:
            self.clear()
            self.header("Módulo 1: Catálogo e Inventario de Activos")
            print(f"\n{BOLD}GESTIÓN DE EQUIPOS Y ACTIVOS{RESET}")
            print(f" {CYAN}[1]{RESET} Listar todos los equipos")
            print(f" {CYAN}[2]{RESET} Registrar nuevo equipo")
            print(f" {CYAN}[3]{RESET} Buscar equipo (Código, Nombre o Área)")
            print(f" {CYAN}[4]{RESET} Modificar estado o datos de equipo")
            print(f" {CYAN}[5]{RESET} Eliminar equipo")
            print(f" {CYAN}[0]{RESET} Volver al Menú Principal")
            print(f"{GRAY}───────────────────────────────────────────────────────────────────────────────{RESET}")

            opt = input(f"{BOLD}Seleccione una opción: {RESET}").strip()
            if opt == "1":
                self.list_equipments_view()
            elif opt == "2":
                self.register_equipment_view()
            elif opt == "3":
                self.search_equipment_view()
            elif opt == "4":
                self.update_equipment_view()
            elif opt == "5":
                self.delete_equipment_view()
            elif opt == "0":
                break

    def list_equipments_view(self, custom_list=None):
        self.clear()
        self.header("Inventario de Equipos Registrados")
        equipments = custom_list if custom_list is not None else self.eq_service.get_all_equipments()

        if not equipments:
            print(f"\n{YELLOW}No se encontraron equipos registrados.{RESET}")
            print(f"{GRAY}Sugerencia: Use la opción [2] para registrar uno o cargue datos demo.{RESET}")
            self.pause()
            return

        print(f"\n{BOLD}{'CÓDIGO':<10} │ {'NOMBRE DEL EQUIPO':<28} │ {'TIPO':<14} │ {'UBICACIÓN':<18} │ {'HORAS':<8} │ {'ESTADO'}{RESET}")
        print(f"{GRAY}───────────┼──────────────────────────────┼────────────────┼────────────────────┼──────────┼──────────────{RESET}")

        for eq in equipments:
            status_badge = colorize_status(eq.status)
            print(
                f"{CYAN}{truncate(eq.code, 10):<10}{RESET} │ "
                f"{truncate(eq.name, 28):<28} │ "
                f"{truncate(eq.type, 14):<14} │ "
                f"{truncate(eq.location, 18):<18} │ "
                f"{eq.operating_hours:>7.1f}h │ "
                f"{status_badge}"
            )
        print(f"{GRAY}───────────┴──────────────────────────────┴────────────────┴────────────────────┴──────────┴──────────────{RESET}")
        print(f"{GRAY}Total de equipos listados: {len(equipments)}{RESET}")
        self.pause()

    def register_equipment_view(self):
        self.clear()
        self.header("Registro de Nuevo Activo Industrial")
        print(f"\n{BOLD}{YELLOW}▶ INGRESE LOS DATOS DEL EQUIPO{RESET}\n")

        code = input(f" {BOLD}• Código de Activo{RESET} (ej. CMP-002, BOM-101)  : ").strip().upper()
        name = input(f" {BOLD}• Nombre o Descripción{RESET} (ej. Bomba de Agua)   : ").strip()
        eq_type = input(f" {BOLD}• Tipo / Disciplina{RESET}    (ej. Hidráulico)       : ").strip()
        location = input(f" {BOLD}• Ubicación en Planta{RESET}  (ej. Nave 2)           : ").strip()
        hours_str = input(f" {BOLD}• Horas de Operación{RESET}   (ej. 1500) [Def: 0.0]  : ").strip()

        hours = 0.0
        if hours_str:
            try:
                hours = float(hours_str)
            except ValueError:
                print(f"{YELLOW}[AVISO] Horas inválidas, se asignará 0.0.{RESET}")

        try:
            eq = self.eq_service.register_equipment(code, name, eq_type, location, hours)
            print(f"\n{GREEN}✔ ÉXITO: Equipo '{eq.name}' [{eq.code}] registrado correctamente en la base de datos.{RESET}")
        except Exception as err:
            print(f"\n{RED}[ERROR] {err}{RESET}")
        self.pause()

    def search_equipment_view(self):
        self.clear()
        self.header("Búsqueda de Activos")
        query = input(f"\n{BOLD}Ingrese término a buscar (Código, Nombre, Tipo o Ubicación): {RESET}").strip()
        if not query:
            return
        results = self.eq_service.search_equipments(query)
        self.list_equipments_view(custom_list=results)

    def update_equipment_view(self):
        self.clear()
        self.header("Actualización de Datos de Equipo")
        code = input(f"\n{BOLD}Ingrese el código del equipo a editar: {RESET}").strip().upper()
        eq = self.eq_service.get_equipment_by_code(code)
        if not eq:
            print(f"\n{RED}[ERROR] No existe ningún equipo con código '{code}'.{RESET}")
            self.pause()
            return

        print(f"\n{BOLD}Datos actuales:{RESET}")
        print(f" • Nombre: {eq.name} | Tipo: {eq.type} | Ubicación: {eq.location} | Estado: {colorize_status(eq.status)} | Horas: {eq.operating_hours}")
        print(f"\n{GRAY}(Deje en blanco los campos que no desee modificar){RESET}\n")

        new_name = input(f" {BOLD}• Nuevo Nombre{RESET} [{eq.name}]: ").strip()
        new_type = input(f" {BOLD}• Nuevo Tipo{RESET} [{eq.type}]: ").strip()
        new_loc = input(f" {BOLD}• Nueva Ubicación{RESET} [{eq.location}]: ").strip()
        print(f" {BOLD}• Opciones de Estado:{RESET} OPERATIONAL, MAINTENANCE, DOWN, WARNING")
        new_status = input(f" {BOLD}• Nuevo Estado{RESET} [{eq.status}]: ").strip().upper()
        new_hours = input(f" {BOLD}• Horas Acumuladas{RESET} [{eq.operating_hours}]: ").strip()

        hours_val = float(new_hours) if new_hours else None
        success = self.eq_service.update_equipment(
            code=code,
            name=new_name if new_name else None,
            eq_type=new_type if new_type else None,
            location=new_loc if new_loc else None,
            status=new_status if new_status else None,
            operating_hours=hours_val,
        )
        if success:
            print(f"\n{GREEN}✔ ÉXITO: El equipo '{code}' fue actualizado correctamente.{RESET}")
        else:
            print(f"\n{RED}[ERROR] No se pudo actualizar el equipo.{RESET}")
        self.pause()

    def delete_equipment_view(self):
        self.clear()
        self.header("Eliminar Activo")
        code = input(f"\n{BOLD}{RED}Ingrese el código del equipo a eliminar: {RESET}").strip().upper()
        eq = self.eq_service.get_equipment_by_code(code)
        if not eq:
            print(f"\n{RED}[ERROR] Equipo no encontrado.{RESET}")
            self.pause()
            return

        confirm = input(f"{YELLOW}¿Está seguro de eliminar '{eq.name}' [{eq.code}] y su historial de OTs? (s/N): {RESET}").strip().lower()
        if confirm == "s":
            if self.eq_service.delete_equipment(code):
                print(f"\n{GREEN}✔ ÉXITO: El equipo y sus registros asociados fueron eliminados.{RESET}")
            else:
                print(f"\n{RED}[ERROR] Error al eliminar.{RESET}")
        else:
            print(f"\n{GRAY}Operación cancelada.{RESET}")
        self.pause()

    # =========================================================================
    # 2. GESTIÓN DE ÓRDENES DE TRABAJO (OT)
    # =========================================================================
    def menu_work_orders(self):
        while True:
            self.clear()
            self.header("Módulo 2: Gestión de Órdenes de Trabajo (OT)")
            print(f"\n{BOLD}ÓRDENES DE TRABAJO (WORK ORDERS){RESET}")
            print(f" {CYAN}[1]{RESET} Listar todas las Órdenes de Trabajo")
            print(f" {CYAN}[2]{RESET} Listar OTs Activas (Pendientes / En Progreso)")
            print(f" {CYAN}[3]{RESET} Crear nueva Orden de Trabajo")
            print(f" {CYAN}[4]{RESET} Iniciar OT (Pasa a En Progreso y equipo a Mantenimiento)")
            print(f" {CYAN}[5]{RESET} Cerrar / Finalizar OT (Registrar horas de paro y costo)")
            print(f" {CYAN}[6]{RESET} Cancelar OT")
            print(f" {CYAN}[0]{RESET} Volver al Menú Principal")
            print(f"{GRAY}───────────────────────────────────────────────────────────────────────────────{RESET}")

            opt = input(f"{BOLD}Seleccione una opción: {RESET}").strip()
            if opt == "1":
                self.list_work_orders_view()
            elif opt == "2":
                self.list_work_orders_view(filter_active=True)
            elif opt == "3":
                self.create_work_order_view()
            elif opt == "4":
                self.start_work_order_view()
            elif opt == "5":
                self.close_work_order_view()
            elif opt == "6":
                self.cancel_work_order_view()
            elif opt == "0":
                break

    def list_work_orders_view(self, filter_active=False):
        self.clear()
        title = "Órdenes de Trabajo Activas" if filter_active else "Historial de Órdenes de Trabajo"
        self.header(title)

        all_ots = self.wo_service.get_all_work_orders()
        if filter_active:
            ots = [o for o in all_ots if o.status in ("PENDING", "IN_PROGRESS")]
        else:
            ots = all_ots

        if not ots:
            print(f"\n{YELLOW}No se encontraron órdenes de trabajo registradas.{RESET}")
            self.pause()
            return

        print(f"\n{BOLD}{'ID':<4} │ {'EQUIPO':<10} │ {'TIPO':<12} │ {'PRIORIDAD':<9} │ {'ESTADO':<12} │ {'TÉCNICO':<18} │ {'TÍTULO'}{RESET}")
        print(f"{GRAY}─────┼────────────┼──────────────┼───────────┼──────────────┼────────────────────┼────────────────────────{RESET}")

        for o in ots:
            status_badge = colorize_status(o.status)
            prio_badge = colorize_status(o.priority)
            print(
                f"{o.id:<4} │ "
                f"{CYAN}{truncate(o.equipment_code, 10):<10}{RESET} │ "
                f"{truncate(o.type, 12):<12} │ "
                f"{prio_badge:<9} │ "
                f"{status_badge:<12} │ "
                f"{truncate(o.assigned_technician, 18):<18} │ "
                f"{truncate(o.title, 24)}"
            )
        print(f"{GRAY}─────┴────────────┴──────────────┴───────────┴──────────────┴────────────────────┴────────────────────────{RESET}")
        print(f"{GRAY}Total de órdenes: {len(ots)}{RESET}")
        self.pause()

    def create_work_order_view(self):
        self.clear()
        self.header("Creación de Orden de Trabajo")
        print(f"\n{BOLD}{YELLOW}▶ DATOS DE LA NUEVA INTERVENCIÓN{RESET}\n")

        eq_code = input(f" {BOLD}• Código del Equipo{RESET} (ej. CMP-001): ").strip().upper()
        if not self.eq_service.get_equipment_by_code(eq_code):
            print(f"\n{RED}[ERROR] El equipo '{eq_code}' no existe en el catálogo.{RESET}")
            self.pause()
            return

        title = input(f" {BOLD}• Título / Asunto de la OT{RESET}      : ").strip()
        desc = input(f" {BOLD}• Descripción de la Falla/Tarea{RESET}   : ").strip()

        print(f"\n {BOLD}Tipos:{RESET} [1] PREVENTIVE  [2] CORRECTIVE  [3] PREDICTIVE")
        t_choice = input(f" {BOLD}• Seleccione Tipo [1-3]{RESET} (Def: 1): ").strip()
        order_type = MaintenanceType.PREVENTIVE.value
        if t_choice == "2":
            order_type = MaintenanceType.CORRECTIVE.value
        elif t_choice == "3":
            order_type = MaintenanceType.PREDICTIVE.value

        print(f" {BOLD}Prioridades:{RESET} [1] LOW  [2] MEDIUM  [3] HIGH  [4] CRITICAL")
        p_choice = input(f" {BOLD}• Seleccione Prioridad [1-4]{RESET} (Def: 2): ").strip()
        prio = Priority.MEDIUM.value
        if p_choice == "1":
            prio = Priority.LOW.value
        elif p_choice == "3":
            prio = Priority.HIGH.value
        elif p_choice == "4":
            prio = Priority.CRITICAL.value

        technician = input(f" {BOLD}• Técnico Responsable{RESET} (Def: Técnico de Turno): ").strip()
        if not technician:
            technician = "Técnico de Turno"

        try:
            wo = self.wo_service.create_work_order(
                equipment_code=eq_code,
                title=title,
                description=desc,
                order_type=order_type,
                priority=prio,
                assigned_technician=technician,
            )
            print(f"\n{GREEN}✔ ÉXITO: Orden de Trabajo OT #{wo.id} generada con estado PENDING.{RESET}")
        except Exception as err:
            print(f"\n{RED}[ERROR] {err}{RESET}")
        self.pause()

    def start_work_order_view(self):
        self.clear()
        self.header("Iniciar Ejecución de Orden de Trabajo")
        wo_id_str = input(f"\n{BOLD}Ingrese el ID de la OT a iniciar: {RESET}").strip()
        try:
            wo_id = int(wo_id_str)
            wo = self.wo_service.get_work_order_by_id(wo_id)
            if not wo:
                print(f"\n{RED}[ERROR] No existe la OT #{wo_id}.{RESET}")
            elif wo.status != "PENDING":
                print(f"\n{YELLOW}[AVISO] La OT #{wo_id} no está en estado PENDING (Estado actual: {wo.status}).{RESET}")
            else:
                self.wo_service.start_work_order(wo_id)
                print(f"\n{GREEN}✔ ÉXITO: OT #{wo_id} ahora está en progreso (IN_PROGRESS).{RESET}")
                print(f"{BLUE}ℹ El equipo '{wo.equipment_code}' cambió su estado a 'MAINTENANCE'.{RESET}")
        except ValueError:
            print(f"\n{RED}[ERROR] ID numérico inválido.{RESET}")
        self.pause()

    def close_work_order_view(self):
        self.clear()
        self.header("Cierre y Liquidación de Orden de Trabajo")
        wo_id_str = input(f"\n{BOLD}Ingrese el ID de la OT a finalizar: {RESET}").strip()
        try:
            wo_id = int(wo_id_str)
            wo = self.wo_service.get_work_order_by_id(wo_id)
            if not wo:
                print(f"\n{RED}[ERROR] No existe la OT #{wo_id}.{RESET}")
                self.pause()
                return

            if wo.status == "COMPLETED":
                print(f"\n{YELLOW}[AVISO] La OT #{wo_id} ya se encuentra cerrada.{RESET}")
                self.pause()
                return

            print(f"\n{BOLD}Detalles de la Orden:{RESET}")
            print(f" Equipo: {wo.equipment_code} | Título: {wo.title} | Tipo: {wo.type}")

            hours_input = input(f"\n {BOLD}• Horas de paro real de la máquina (Downtime){RESET} [ej: 2.5]: ").strip()
            cost_input = input(f" {BOLD}• Costo total de repuestos y mano de obra ($){RESET} [ej: 180.0]: ").strip()

            hours = float(hours_input) if hours_input else 0.0
            cost = float(cost_input) if cost_input else 0.0

            self.wo_service.close_work_order(wo_id, downtime_hours=hours, cost=cost)
            print(f"\n{GREEN}✔ ÉXITO: La OT #{wo_id} fue cerrada como COMPLETED.{RESET}")
            print(f"{GREEN}ℹ Si no quedan otras OTs activas, el equipo '{wo.equipment_code}' vuelve a 'OPERATIONAL'.{RESET}")
        except ValueError:
            print(f"\n{RED}[ERROR] Datos numéricos inválidos.{RESET}")
        self.pause()

    def cancel_work_order_view(self):
        self.clear()
        self.header("Cancelar Orden de Trabajo")
        wo_id_str = input(f"\n{BOLD}Ingrese el ID de la OT a cancelar: {RESET}").strip()
        try:
            wo_id = int(wo_id_str)
            if self.wo_service.cancel_work_order(wo_id):
                print(f"\n{GREEN}✔ ÉXITO: La OT #{wo_id} fue cancelada.{RESET}")
            else:
                print(f"\n{RED}[ERROR] No se pudo cancelar la orden.{RESET}")
        except ValueError:
            print(f"\n{RED}[ERROR] ID inválido.{RESET}")
        self.pause()

    # =========================================================================
    # 3. INDICADORES Y KPIS INDUSTRIALES
    # =========================================================================
    def menu_kpis(self):
        self.clear()
        self.header("Módulo 3: Indicadores y KPIs Industriales")
        kpi = self.metrics_service.get_plant_kpis()

        # Visual progress bar for Availability
        pct = kpi["availability_pct"]
        bar_len = 30
        filled = int((pct / 100.0) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        bar_color = GREEN if pct >= 90 else (YELLOW if pct >= 75 else RED)

        print(f"\n{BOLD}═════════════════ MÉTRICAS GENERALES DE PLANTA ═════════════════{RESET}")
        print(f" • Total de Activos Registrados : {BOLD}{CYAN}{kpi['total_equipments']}{RESET}")
        print(f" • Horas Operativas Totales     : {kpi['total_operating_hours']:.1f} horas acumuladas")
        print(f" • Órdenes de Trabajo Activas   : {YELLOW}{kpi['active_work_orders']}{RESET} (Pendientes / En Proceso)")
        print(f" • Fallas Correctivas Históricas: {RED}{kpi['corrective_failures']}{RESET}")
        print(f" • Tiempo Total de Paro (Downtime): {kpi['corrective_downtime_hours']:.1f} horas")
        print(f" • Gasto Total en Mantenimiento : {GREEN}${kpi['total_cost']:,.2f} USD{RESET}")

        print(f"\n{BOLD}═══════════════════ KPIS DE CONFIABILIDAD ═══════════════════{RESET}")
        print(f" 📈 {BOLD}MTBF{RESET} (Mean Time Between Failures) : {BOLD}{CYAN}{kpi['mtbf_hours']}{RESET} horas entre fallas")
        print(f" ⏱️  {BOLD}MTTR{RESET} (Mean Time To Repair)        : {BOLD}{YELLOW}{kpi['mttr_hours']}{RESET} horas para reparar")
        print(f" ⚡ {BOLD}DISPONIBILIDAD OPERATIVA{RESET}       : {bar_color}[{bar}] {pct:.2f}%{RESET}")
        print(f"{GRAY}───────────────────────────────────────────────────────────────────────────────{RESET}")

        # Sub-option: detail per equipment
        print(f"\n{BOLD}Opciones:{RESET}")
        print(f" [1] Ver KPIs detallados de un equipo específico")
        print(f" [0] Volver al Menú Principal")

        choice = input(f"{BOLD}Seleccione una opción: {RESET}").strip()
        if choice == "1":
            code = input(f"{BOLD}Código del equipo a consultar: {RESET}").strip().upper()
            try:
                eq_kpi = self.metrics_service.get_equipment_kpis(code)
                print(f"\n{BOLD}Indicadores para {eq_kpi['name']} [{eq_kpi['code']}]:{RESET}")
                print(f" • Estado Actual      : {colorize_status(eq_kpi['status'])}")
                print(f" • Horas Operadas     : {eq_kpi['operating_hours']:.1f} h")
                print(f" • Fallas Correctivas : {eq_kpi['corrective_failures']}")
                print(f" • Tiempo de Paro     : {eq_kpi['downtime_hours']} h")
                print(f" • Costo Acumulado    : ${eq_kpi['total_cost']:.2f}")
                print(f" • MTBF               : {eq_kpi['mtbf']} h")
                print(f" • MTTR               : {eq_kpi['mttr']} h")
                print(f" • Disponibilidad     : {GREEN if eq_kpi['availability'] >= 90 else YELLOW}{eq_kpi['availability']}%{RESET}")
            except Exception as e:
                print(f"{RED}[ERROR] {e}{RESET}")
            self.pause()

    # =========================================================================
    # 4. EXPORTACIÓN DE REPORTES CSV
    # =========================================================================
    def menu_export(self):
        self.clear()
        self.header("Módulo 4: Exportación de Reportes a CSV")
        print(f"\n{BOLD}EXPORTACIÓN DE DATOS{RESET}")
        print("Este proceso genera archivos .CSV compatibles con Excel, Power BI y Google Sheets.")
        confirm = input(f"\n{BOLD}¿Desea generar los reportes ahora? (S/n): {RESET}").strip().lower()

        if confirm != "n":
            try:
                eq_file, wo_file = self.export_service.export_all_to_csv()
                print(f"\n{GREEN}✔ ÉXITO: Reportes generados correctamente:{RESET}")
                print(f" 📄 Inventario de Equipos : {CYAN}{eq_file}{RESET}")
                print(f" 📄 Historial de OTs      : {CYAN}{wo_file}{RESET}")
            except Exception as err:
                print(f"\n{RED}[ERROR al exportar] {err}{RESET}")
        self.pause()

    # =========================================================================
    # 5. MONITOR IOT / ARDUINO
    # =========================================================================
    def menu_iot(self):
        while True:
            self.clear()
            self.header("Módulo 5: Monitor de Telemetría IoT & Sensores Arduino")
            print(f"\n{BOLD}MONITOREO DE CONDICIÓN EN TIEMPO REAL{RESET}")
            serial_status = f"{GREEN}Disponible{RESET}" if self.iot_service.is_serial_available() else f"{YELLOW}No instalado (pyserial opcional){RESET}"
            print(f" Soporte Serial Físico: {serial_status}")
            print(f" {CYAN}[1]{RESET} Simular lectura sensorial normal (Temperatura y Vibración ISO 10816)")
            print(f" {CYAN}[2]{RESET} Inyectar anomalía crítica (Disparar Alarma y OT Predictiva)")
            print(f" {CYAN}[3]{RESET} Conectar a puerto Serial de Arduino físico")
            print(f" {CYAN}[0]{RESET} Volver al Menú Principal")
            print(f"{GRAY}───────────────────────────────────────────────────────────────────────────────{RESET}")

            opt = input(f"{BOLD}Seleccione una opción: {RESET}").strip()
            if opt in ("1", "2"):
                equipments = self.eq_service.get_all_equipments()
                if not equipments:
                    print(f"\n{YELLOW}Registre o cargue equipos antes de monitorear.{RESET}")
                    self.pause()
                    continue

                code = input(f"Código del equipo a censar [{equipments[0].code}]: ").strip().upper()
                if not code:
                    code = equipments[0].code

                inject = (opt == "2")
                reading, severity, wo_id = self.iot_service.simulate_telemetry_reading(code, inject_anomaly=inject)

                print(f"\n{BOLD}LECTURA DE TELEMETRÍA RECIBIDA:{RESET}")
                print(f" • Equipo     : {CYAN}{reading.equipment_code}{RESET}")
                print(f" • Temperatura: {reading.temperature} °C  {'(Normal < 70°C)' if reading.temperature < 70 else (RED + '¡ALERTA CALOR!' + RESET)}")
                print(f" • Vibración  : {reading.vibration} mm/s {'(Normal < 4.5 mm/s)' if reading.vibration < 4.5 else (RED + '¡ALERTA VIBRACIÓN ISO!' + RESET)}")
                print(f" • Corriente  : {reading.current} A")
                print(f" • Diagnóstico: {colorize_status(severity)}")

                if wo_id:
                    print(f"\n{BG_RED}{WHITE} ¡ALERTA DISPARADA! {RESET} Se generó automáticamente la {BOLD}OT Predictiva #{wo_id}{RESET}.")
                    print(f"El equipo ha sido marcado como {colorize_status(severity)} en el sistema.")
                else:
                    print(f"\n{GREEN}✔ Parámetros dentro de los rangos normales de operación.{RESET}")
                self.pause()

            elif opt == "3":
                if not self.iot_service.is_serial_available():
                    print(f"\n{YELLOW}[AVISO] Para leer hardware físico, instale pyserial: pip install pyserial{RESET}")
                else:
                    port = input("Ingrese el puerto COM del Arduino (ej. COM3 o COM4): ").strip()
                    try:
                        print(f"{GRAY}Escuchando puerto {port} a 9600 baud...{RESET}")
                        data = self.iot_service.read_real_serial_line(port)
                        if data:
                            print(f"{GREEN}Dato recibido:{RESET} {data}")
                        else:
                            print(f"{YELLOW}No se recibieron datos en el puerto.{RESET}")
                    except Exception as e:
                        print(f"{RED}[ERROR SERIAL] {e}{RESET}")
                self.pause()

            elif opt == "0":
                break

    # =========================================================================
    # 6. CARGAR DATOS DEMO
    # =========================================================================
    def load_demo(self):
        self.clear()
        self.header("Carga de Datos de Demostración")
        print(f"\n{BOLD}Poblar Base de Datos con Activos y Órdenes de Prueba{RESET}")
        eq_count = self.eq_service.load_demo_data()
        wo_count = self.wo_service.load_demo_work_orders()

        print(f"\n{GREEN}✔ ÉXITO: Base de datos inicializada.{RESET}")
        print(f" • Equipos incorporados         : {BOLD}{eq_count}{RESET}")
        print(f" • Órdenes de Trabajo generadas : {BOLD}{wo_count}{RESET}")
        print(f"{GRAY}Ahora puede explorar el catálogo, las OTs y las métricas con datos reales.{RESET}")
        self.pause()

    # =========================================================================
    # CICLO PRINCIPAL
    # =========================================================================
    def run(self):
        while True:
            self.clear()
            self.header("Panel de Control Principal")
            print(f"\n{BOLD}MENÚ PRINCIPAL{RESET}")
            print(f" {CYAN}[1]{RESET} 📦 Gestión de Equipos y Activos")
            print(f" {CYAN}[2]{RESET} 🛠️  Gestión de Órdenes de Trabajo (OT)")
            print(f" {CYAN}[3]{RESET} 📊 Indicadores y KPIs Industriales (MTBF, MTTR, Disponibilidad)")
            print(f" {CYAN}[4]{RESET} 💾 Exportación de Reportes a CSV")
            print(f" {CYAN}[5]{RESET} ⚡ Monitor de Telemetría IoT / Arduino")
            print(f" {CYAN}[6]{RESET} 🧪 Cargar Datos de Demostración (Demo)")
            print(f" {RED}[0]{RESET} 🚪 Salir del Sistema")
            print(f"{GRAY}───────────────────────────────────────────────────────────────────────────────{RESET}")

            choice = input(f"{BOLD}Seleccione un módulo [0-6]: {RESET}").strip()
            if choice == "1":
                self.menu_equipment()
            elif choice == "2":
                self.menu_work_orders()
            elif choice == "3":
                self.menu_kpis()
            elif choice == "4":
                self.menu_export()
            elif choice == "5":
                self.menu_iot()
            elif choice == "6":
                self.load_demo()
            elif choice == "0":
                self.clear()
                print(f"\n{GREEN}Sistema de Mantenimiento Industrial cerrado de forma segura.{RESET}")
                print(f"{GRAY}Los datos fueron persistidos en SQLite (data/cmms.db). ¡Hasta pronto!\n{RESET}")
                sys.exit(0)


def run_app():
    """Entry point helper to launch CMMS CLI."""
    app = CMMSApp()
    app.run()
