[README.md](https://github.com/user-attachments/files/32483819/README.md)
# 🏭 CMMS Industrial v2.0 - Sistema de Gestión de Mantenimiento & Telemetría IoT

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![Deploy](https://img.shields.io/badge/Deploy-Vercel%20Serverless-black.svg)](https://vercel.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Sistema integral de gestión de mantenimiento asistido por computadora (**CMMS**) diseñado para plantas industriales. Incluye administración de activos, órdenes de trabajo (OT), telemetría IoT / Arduino con mantenimiento predictivo, cálculo de confiabilidad (MTBF, MTTR, Disponibilidad), control de acceso por roles (**RBAC**) y portal web táctil optimizado para técnicos de campo en dispositivos móviles.

---

## 🌟 Características Destacadas

### 1. 👑 Panel de Control para Administradores
* **Gestión de Activos (CRUD):** Registro, monitoreo de horas operativas y control de estados (`OPERATIONAL`, `MAINTENANCE`, `DOWN`, `WARNING`).
* **Órdenes de Trabajo (OT):** Planificación de mantenimientos preventivos, correctivos y predictivos con prioridades y asignación de técnicos.
* **KPIs y Confiabilidad:** Cálculo en tiempo real de **MTBF**, **MTTR**, **Disponibilidad Operativa (%)** y análisis de costos.
* **Telemetría IoT & Arduino:** Lectura serial directa y simulador de sensores de Temperatura (°C), Vibración RMS (ISO 10816) y Corriente (A).
* **Reportes:** Exportación con un clic a archivos `.csv` compatibles con Excel y Power BI.

### 2. 📱 Portal Móvil & Tablet para Técnicos de Campo
* **Acceso Táctil:** Diseñado para smartphones y tablets en planta sin necesidad de instalar aplicaciones nativas.
* **Privacidad Estricta (RBAC):** Cada técnico **solo ve las órdenes asignadas a su nombre** y las órdenes libres de planta.
* **Autoasignación en Tiempo Real:** Pestaña *"Disponibles para Todos ✋"* con botón interactivo para autoasignarse órdenes con un toque.
* **Informe Guiado de Cierre:** Al finalizar el trabajo, el técnico registra qué se hizo en la máquina y qué repuestos/materiales se utilizaron.

### 3. 🔐 Seguridad, Control de Acceso (RBAC) & Cambio de Clave
* Autenticación con contraseñas seguras cifradas mediante **PBKDF2-HMAC-SHA256**.
* Tokens de sesión firmados sin dependencias externas pesadas.
* **🔒 Cambio de Contraseña Integrado:** Los usuarios pueden actualizar su contraseña en cualquier momento con validación en tiempo real de seguridad industrial (mínimo 8 caracteres, mayúsculas, minúsculas, números/símbolos y medidor dinámico de fortaleza).
* Cuentas de demostración preconfiguradas:
  * **Administrador:** `admin` / `admin123`
  * **Técnico Mecánico:** `carlos` / `1234` (Ing. Carlos Mendoza)
  * **Técnico Eléctrico:** `laura` / `1234` (Tec. Laura Ramos)
  * **Técnico Predictivo:** `andres` / `1234` (Tec. Andrés Silva)

### 4. 🏭 Datos de Demostración Industriales
* **8 Equipos de Planta:** Compresor Rotativo GA-75, Bomba KSB-80, Motor Siemens 75HP, Cinta Mod-B, Caldera 500BHP, Extrusora Doble Husillo 120mm, Torre de Enfriamiento 350TR y Generador Cummins 450kVA.
* **13 Órdenes de Trabajo:** Cobertura de las 3 categorías (`PREVENTIVE`, `CORRECTIVE`, `PREDICTIVE`) para cada técnico, historial de órdenes cerradas con informe técnico y repuestos usados, más 4 órdenes disponibles en *"Disponibles para Todos ✋"*.

### 5. ☁️ Preparado para la Nube (Vercel & GitHub)
* Compatible con **Vercel Serverless Python** (`@vercel/python` y `vercel.json`).
* Base de datos adaptable para entornos de solo lectura en la nube (`/tmp/cmms.db`).
* **Cero dependencias obligatorias:** Funciona al 100% con la biblioteca estándar de Python.

---

## 🏛️ Estructura del Repositorio

```text
industrial-maintenance-system/
├── api/
│   └── index.py                # Entrada Serverless para despliegue en Vercel
├── data/
│   ├── cmms.db                 # Base de datos relacional SQLite
│   └── notifications_config.json
├── src/
│   ├── database/               # Esquema relacional y gestor de conexiones
│   ├── models/                 # Entidades de dominio (User, Equipment, WorkOrder)
│   ├── services/               # Lógica de negocio (Auth, OTs, Equipos, KPIs, IoT)
│   ├── ui/                     # Interfaz de terminal interactiva CLI
│   └── web/                    # Servidor HTTP REST API y Frontend Web
│       └── static/             # Vistas HTML, CSS táctil y módulos JS
│           ├── index.html      # Panel General del Administrador
│           ├── tecnico.html    # Portal Móvil del Técnico
│           └── login.html      # Pantalla de Autenticación Unificada
├── tests/                      # Suite de pruebas automatizadas (20 tests)
├── run_web.py                  # Lanzador del servidor web local
├── main.py                     # Lanzador de la interfaz de terminal CLI
├── vercel.json                 # Configuración de despliegue en Vercel
├── requirements.txt            # Dependencias opcionales (pyserial)
└── README.md
```

---

## 🚀 Inicio Rápido (Local)

### 1. Clonar o descargar el proyecto
```bash
git clone https://github.com/TU_USUARIO/industrial-cmms.git
cd industrial-cmms
```

### 2. Iniciar la Aplicación Web
```bash
python run_web.py
```
El navegador se abrirá automáticamente en:
* **Pantalla de Acceso / Login:** [http://localhost:5000/login](http://localhost:5000/login)
* **Panel General (Admin):** [http://localhost:5000/](http://localhost:5000/)
* **Portal Móvil de Técnicos:** [http://localhost:5000/tecnico](http://localhost:5000/tecnico)

*(Opcional: Si prefieres la consola de terminal, ejecuta `python main.py`).*

---

## 🌐 Despliegue en la Nube con Vercel

1. Sube este repositorio a tu cuenta de **GitHub**.
2. Ingresa a [vercel.com](https://vercel.com) e inicia sesión con GitHub.
3. Haz clic en **"Add New..."** ➔ **"Project"** y selecciona este repositorio.
4. Presiona **"Deploy"**. En menos de un minuto tendrás tu aplicación funcionando en Internet con HTTPS seguro.

---

## 🧪 Pruebas Automatizadas

Para correr toda la suite de pruebas unitarias y de integración:
```bash
python -m unittest discover tests
```
*20 pruebas cubriendo autenticación, cambio de contraseña segura, filtrado estricto por roles, KPIs y telemetría IoT.*

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.
