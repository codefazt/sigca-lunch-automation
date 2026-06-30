# Design: Arquitectura Técnica y Programación en Windows 11

**ID del Cambio:** 001-daily-lunch-automation  
**Fecha:** 2026-06-17  
**Estado:** Propuesto  

---

## 1. Arquitectura de Archivos y Componentes

El proyecto seguirá la siguiente estructura modular en la raíz del espacio de trabajo:

```text
solicitud_almuerzo_auto/
├── openspec/                     # Configuración y ciclo de vida SDD
│   ├── config.yaml
│   └── changes/001-daily-lunch-automation/
│       ├── proposal.md
│       ├── specs.md
│       ├── design.md
│       ├── tasks.md
│       └── verify.md
├── logs/                         # Archivos de logs diarios
│   └── lunch_automation.log
├── evidence/                     # Capturas de pantalla históricas
│   └── *.png
├── tests/                        # Pruebas automatizadas (TDD)
│   ├── conftest.py
│   └── test_lunch_bot.py
├── .env.template                 # Plantilla para variables de entorno
├── .env                          # Credenciales reales (fuera de Git)
├── config.json                   # Parámetros del bot (horarios, timeouts, reintentos)
├── lunch_bot.py                  # Script principal de automatización
├── run_job.bat                   # Ejecutor ejecutable por Windows Task Scheduler
└── requirements.txt              # Dependencias de Python
```

---

## 2. Detalle de los Módulos y Código

### 2.1. Configuración de Parámetros (`config.json`)
Permite configurar el comportamiento del bot sin modificar el código:
```json
{
  "start_hour": 16,
  "end_hour": 22,
  "timeout_ms": 30000,
  "headless": true,
  "retries": 3,
  "retry_delay_sec": 300
}
```

### 2.2. Script Principal (`lunch_bot.py`)
Utilizará la API síncrona de **Playwright** para mantener la lógica lineal y fácil de depurar en entornos de servidor.

**Clase `LunchBot`:**
- `__init__(self)`: Carga las variables de entorno y `config.json`. Inicializa Playwright y el navegador.
- `is_time_valid(self)`: Verifica que la hora local esté dentro de la ventana de tiempo (por defecto 16:00 - 22:00).
- `login(self, page)`: Realiza el flujo de login rellenando el email y password, esperando que la SPA cargue.
- `check_already_requested(self, page)`: Analiza el dashboard para ver si ya se solicitó el almuerzo (buscando texto o botones inhabilitados).
- `request_lunch(self, page)`: Realiza clic en los botones de selección del menú y confirma el almuerzo.
- `capture_evidence(self, page, name)`: Guarda una captura de pantalla en `evidence/`.
- `run(self)`: Método orquestador. Retorna código de salida (0 para éxito, >=1 para errores).

### 2.3. Seguridad y Credenciales
El script cargará credenciales usando `python-dotenv`:
```bash
SIGCA_USER=johan.carmino@ex-cle.com
SIGCA_PASSWORD=Johan2022.
SIGCA_URL=https://sigca.ex-cle.com/
```
El archivo `.gitignore` excluirá estrictamente el archivo `.env` para evitar subidas de contraseñas accidentales.

---

## 3. Integración con Windows 11 Task Scheduler

Para ejecutar el job de forma desatendida diariamente:

### 3.1. Lanzador `run_job.bat`
Este script configura el entorno de ejecución antes de lanzar el bot de Python:
```batch
@echo off
cd /d "c:\Users\Administrador\Desktop\python\solicitud_almuerzo_auto"
if not exist venv (
    echo Creando entorno virtual Python...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python lunch_bot.py >> logs\launcher.log 2>&1
```

### 3.2. Configuración en la Tarea Programada de Windows (GUI)
1. Abrir **Task Scheduler** (Programador de Tareas).
2. Crear una nueva **Tarea Básica** (Create Basic Task):
   - **Nombre:** `SiGCA Auto Lunch Order`
   - **Trigger:** Daily (Diario)
   - **Hora de inicio:** `16:30:00` (4:30 PM)
   - **Acción:** Start a program (Iniciar un programa)
   - **Programa/script:** `c:\Users\Administrador\Desktop\python\solicitud_almuerzo_auto\run_job.bat`
   - **Iniciar en (Start in):** `c:\Users\Administrador\Desktop\python\solicitud_almuerzo_auto\`
3. Configuración avanzada de la tarea:
   - Marcar: "Run whether user is logged on or not" (Ejecutar tanto si el usuario inició sesión como si no).
   - Marcar: "Run with highest privileges" (Ejecutar con los privilegios más altos, útil para acceso a red en segundo plano).
   - En la pestaña "Settings" (Configuración), configurar: "Stop the task if it runs longer than: 10 minutes". Esto evita procesos colgados si el navegador se queda en bucle.
   - Configurar: "If the task fails, restart every: 10 minutes" (máximo 3 veces).
