"""
Industrial Maintenance Management System (CMMS)
Web Application Launcher with Local Wi-Fi & Mobile Network Support.

Starts the embedded local web server listening on 0.0.0.0 so tablets and smartphones
can connect directly from the company's local Wi-Fi.
No external dependencies required!
"""

import os
from pathlib import Path
import sys
import threading
import time
import webbrowser

# Reconfigure stdout for UTF-8 on Windows console if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.web.server import create_server, get_local_ip


def open_browser(url: str, delay: float = 0.8) -> None:
    """Waits briefly for server to bind then launches default browser."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    host = "0.0.0.0"
    port = 5000
    local_ip = get_local_ip()

    url_local = f"http://localhost:{port}"
    url_login = f"http://localhost:{port}/login"
    url_dashboard_wifi = f"http://{local_ip}:{port}"
    url_technician_mobile = f"http://{local_ip}:{port}/tecnico"

    print("=" * 74)
    print("  SISTEMA DE GESTION DE MANTENIMIENTO INDUSTRIAL (CMMS) - SERVIDOR WEB")
    print("=" * 74)
    print(f" [Acceso / Login]  Pantalla de Ingreso:          {url_login}")
    print(f" [PC Admin]        Panel Administrador:          {url_local}")
    print(f" [MOVIL/TABLET]    Portal Directo para Técnicos: {url_technician_mobile}")
    print(f" [Wi-Fi/Red]       Panel en Red Local:           {url_dashboard_wifi}")
    print("=" * 74)
    print(" Cuentas de Acceso de Demostración:")
    print("  • Administrador:  admin  / admin123  (Acceso total a la planta)")
    print("  • Técnico Campo:  carlos / 1234      (Ing. Carlos Mendoza)")
    print("  • Técnico Campo:  laura  / 1234      (Tec. Laura Ramos)")
    print("  • Técnico Campo:  andres / 1234      (Tec. Andrés Silva)")
    print("=" * 74)
    print(" Presione Ctrl + C para detener el servidor de forma segura.\n")

    # Launch local browser on 127.0.0.1
    threading.Thread(target=open_browser, args=(url_local,), daemon=True).start()

    try:
        server = create_server(host, port)
        server.serve_forever()
    except OSError as err:
        if "address already in use" in str(err).lower() or getattr(err, "winerror", None) == 10048:
            port = 5050
            url_local = f"http://localhost:{port}"
            url_technician_mobile = f"http://{local_ip}:{port}/tecnico"
            print(f"[!] Puerto 5000 ocupado, iniciando en {url_local}...")
            print(f"[MOVIL/TABLET] Portal Tecnico Movil: {url_technician_mobile}")
            threading.Thread(target=open_browser, args=(url_local,), daemon=True).start()
            server = create_server(host, port)
            server.serve_forever()
        else:
            raise
    except KeyboardInterrupt:
        print("\n\nServidor web detenido por el usuario. ¡Hasta pronto!")
        sys.exit(0)


if __name__ == "__main__":
    main()
