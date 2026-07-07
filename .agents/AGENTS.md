# Agent Instructions & Guidelines for SiGCABot

Este archivo centraliza las reglas, directrices de desarrollo, arquitectura y buenas prácticas del proyecto **SiGCABot** (Automatización de Solicitud de Almuerzos en SiGCA).

## 📌 Principios de Diseño y Filosofía del Proyecto

1. **Robustez y Tolerancia a Fallos:** La aplicación ejecuta automatizaciones web complejas interactuando con sistemas corporativos propensos a cambios y lentitud (Microsoft SSO, formularios web). Cada acción de Playwright debe estar protegida contra excepciones y timeouts.
2. **Interfaz Premium y Fluida (No-Blocking GUI):** La interfaz Tkinter nunca debe bloquearse. Toda tarea de automatización, red o temporizador pesado debe ejecutarse en un hilo secundario y comunicarse con el hilo de la interfaz mediante callbacks seguros y la cola `.after()` de Tkinter.
3. **Cumplimiento con Windows:** La aplicación debe integrarse de forma nativa y limpia con Windows (Registro de inicio, Programador de Tareas, System Tray con `pystray`, y Notificaciones Toast nativas).
4. **Seguridad y Privacidad:** Las credenciales nunca se guardan en el código ni en el repositorio. Se cargan y guardan en el archivo `.env`. Si una autenticación falla repetidamente, el bot debe desactivarse automáticamente para evitar el bloqueo de cuentas corporativas.

---

## 🏗️ Arquitectura del Software

El proyecto se divide en el script principal de entrada y un paquete de módulos internos (`src/`):

- **[app_gui.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/app_gui.py):** Punto de entrada. Determina si se ejecuta la interfaz de Tkinter o el modo CLI (`--run-job`, `--cancel-order`) invocado por el programador de tareas de Windows.
- **[src/config.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/config.py):** Gestión de persistencia de configuración (`config.json`, `.env`, `status.json`), variables de colores y auto-inicio.
- **[src/logger.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/logger.py):** Logging centralizado con handlers para archivo, consola y GUI (`GUILogHandler`).
- **[src/bot_engine.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/bot_engine.py):** Lógica del motor Playwright. Formulario de almuerzo, SSO Microsoft, captura de evidencias e inicio/cancelación.
- **[src/scheduler.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/scheduler.py):** Planificador en bucle secundario e integración con el Task Scheduler de Windows.
- **[src/health_server.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/health_server.py):** Servidor HTTP local para monitorización remota y dashboard web de logs en tiempo real.
- **[src/telegram_poller.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/telegram_poller.py):** Escucha e interacción remota mediante comandos de Telegram.
- **[src/notifications.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/notifications.py):** Notificaciones Toast locales y mensajería/fotos de Telegram.
- **[src/state.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/state.py):** Estado global compartido (hilos).

---

## 🛠️ Reglas del Proyecto para el Agente AI

### 1. Modificaciones de Código
- **Preservar Comentarios:** No elimines comentarios o docstrings en español existentes. Mantén el formato de la documentación del proyecto.
- **Evitar Dependencias Circulares:** Al añadir o modificar lógica, asegúrate de no generar dependencias circulares. Para estados globales compartidos entre módulos, utiliza o expande [src/state.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/state.py).
- **Importación de Módulos:** No importes módulos de Tkinter o GUI en archivos del paquete `src/` que corran en modo CLI puro (como `bot_engine.py` o `scheduler.py`). Mantén la interfaz gráfica desacoplada de la lógica del bot.

### 2. Estilo de GUI
- Sigue fielmente la paleta de colores oscura estilo *Hextech Client (LoL)* definida en [src/config.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/config.py):
  - Fondo Principal (`BG_MAIN`): `#010a13`
  - Tarjetas/Paneles (`BG_CARD`): `#091428`
  - Inputs (`BG_INPUT`): `#050c14`
  - Texto (`FG_TEXT`): `#f0e6d2`
  - Accent (`ACCENT`): `#c8aa6e`
  - Estados: Verde/Celeste (`ACCENT_GREEN` - `#0acbe6`), Rojo (`ACCENT_RED` - `#c83232`), Amarillo/Bronce (`ACCENT_YELLOW` - `#785a28`), Azul (`ACCENT_BLUE` - `#005a82`).
- **Diseño de Ventanas Emergentes (Popups) y Alertas:** Nunca utilices `messagebox` estándar de Tkinter. Todas las notificaciones del bot y cajas de confirmación dentro de la GUI deben heredar o instanciar `PremiumMessageBox` o `PremiumConfirmBox` con bordes exteriores de `2px` coloreados según la severidad (`ACCENT_BLUE` para información, `ACCENT_GREEN` para éxito, `ACCENT_YELLOW` para advertencias, y `ACCENT_RED` para errores) y hover dinámico en botones.
- **Regla Anti-Deadlock de Tkinter (Modales):** Nunca utilices `self.wait_window()` dentro del constructor `__init__` de un `Toplevel` que también use `grab_set()`, ya que congelará el Hilo Principal. En su lugar, el objeto de la ventana modal debe instanciarse completamente, y la función llamadora es la responsable de invocar `parent.wait_window(dialog)`.

### 3. Manejo de Procesos y Programación en Windows
- Al interactuar con el Programador de Tareas, genera comandos PowerShell envueltos en codificación Base64 si contienen caracteres especiales o rutas de Windows complejas.
- Garantiza que `PLAYWRIGHT_BROWSERS_PATH` esté correctamente configurado en la carpeta de AppData local del usuario para evitar fallos de ejecución cuando se ejecuta bajo contextos de sistema o tareas programadas de Windows.

