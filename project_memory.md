# Memoria del Proyecto: SiGCABot (Project Memory)

Este archivo registra de forma histórica los avances, logros, fallos detectados y soluciones aplicadas durante el desarrollo de **SiGCABot**.

---

## 🌟 Estado del Proyecto y Avances (Advances & Achievements)

Hasta la fecha (30 de junio de 2026), se han implementado y validado con éxito las siguientes capacidades:

### 1. Interfaz de Usuario Premium
- Diseño en modo oscuro basado en la paleta de colores *Catppuccin*.
- Consola interactiva integrada que muestra logs en tiempo real mediante un handler de logging personalizado (`GUILogHandler`).
- Pestañas organizadas para configurar credenciales corporativas, tokens de Telegram, horarios del planificador y preferencias del menú.
- Integración en la bandeja del sistema (System Tray) con soporte para cerrar la interfaz manteniendo la ejecución en segundo plano y restaurar con doble clic.

### 2. Automatización Resiliente con Playwright
- Flujo de autenticación SSO Microsoft con soporte para múltiples contraseñas (separadas por comas en el `.env`) en caso de expiración o rotación de credenciales.
- Selección automatizada de menús (Saludable/Estándar) y respuesta interactiva a preguntas o formularios dinámicos adicionales.
- Captura de pantalla automática en formato PNG guardada como evidencia física en la carpeta `/evidence`.
- Validación activa contra pedidos duplicados antes de someter el formulario.

### 3. Monitoreo y Telemetría Externa
- Servidor local HTTP de Health Check expuesto en `http://127.0.0.1:18293/health` que responde con estadísticas JSON sobre el estado del bot.
- Dashboard web básico e interactivo en `http://127.0.0.1:18293/` con la visualización en tiempo real de logs y de la última captura de pantalla de evidencia.
- Integración con bot de Telegram asíncrono para enviar notificaciones e imágenes de confirmación, así como comandos interactivos (ej. `/status`, `/health`).

### 4. Automatización en Windows
- Script de compilación `build.bat` que empaqueta todo el entorno, dependencias de Python y assets estáticos en un archivo ejecutable autónomo (`SiGCABot.exe`) mediante PyInstaller.
- Configuración y registro automático de la Tarea Programada de Windows (Task Scheduler) con elevación UAC dinámica para ejecutar la aplicación en segundo plano a las horas planificadas.

### 5. Nuevas Funcionalidades (Versión 2.2.0)
- **Gestión Inteligente de Cancelaciones:** Validación estricta que previene pedidos adicionales en el mismo día tras una cancelación. La restricción se reinicia de manera autónoma al cambiar de día.
- **Modo Solicitud Manual:** Botón dedicado para forzar la petición de almuerzo, esquivando el seguro de cancelación diaria.
- **Auto-Limpieza Semanal:** Tarea del planificador que purga automáticamente logs y capturas de pantalla de la carpeta `evidence/` cuando superan los 7 días de antigüedad.
- **Mantenimiento Manual:** Nueva opción en la interfaz para limpiar inmediatamente todos los registros y evidencias pasadas, preservando únicamente los archivos críticos en uso.
- **Actualización Estética y Empaquetado:** Reparación del error visual de los `Checkbutton` en Windows oscuro mediante el módulo `ttk`, corrección del archivo `build.bat` para evitar bloqueos del sistema operativo (antivirus race conditions) durante la compresión del ejecutable, e inclusión del nuevo arte conceptual de "Bender Chef".

---

## 🐞 Historial de Fallos y Soluciones (Failures & Fixes)

A continuación, se detallan los fallos históricos encontrados en el desarrollo y las soluciones implementadas para resolverlos:

### 1. Error de Ejecutable del Navegador en Tareas Programadas (SYSTEM Context)
* **Fallo:** Al ejecutarse el bot como una Tarea Programada de Windows a través del Task Scheduler, el sistema lo ejecutaba bajo un perfil del sistema o cuenta administrativa diferente. Playwright intentaba buscar los binarios del navegador en la carpeta `C:\WINDOWS\system32\config\systemprofile` y fallaba con `BrowserType.launch: Executable doesn't exist`.
* **Solución:** Se forzó a Playwright en [src/config.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/config.py) a utilizar la ruta global de instalación de navegadores de la cuenta de usuario local de Windows, inyectando la variable de entorno `PLAYWRIGHT_BROWSERS_PATH` que apunta a `~/AppData/Local/ms-playwright` antes de inicializar Playwright.

### 2. Error de Referencia de Variable No Definida (`base64`)
* **Fallo:** En versiones iniciales de [src/scheduler.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/scheduler.py), al registrar tareas en Windows, el script lanzaba un error `NameError: name 'base64' is not defined` al intentar convertir a Base64 la cadena de comandos PowerShell.
* **Solución:** Se corrigieron las importaciones en el encabezado de [src/scheduler.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/scheduler.py) agregando la librería `base64` de la biblioteca estándar de Python.

### 3. Excepción de Denegación de Acceso (`UnauthorizedAccessException`) en el Programador
* **Fallo:** Al pulsar el botón "Registrar Tarea Diaria" desde la GUI sin privilegios administrativos, PowerShell arrojaba una excepción de acceso denegado debido a políticas de ejecución (`ExecutionPolicy`) de Windows o falta de elevación.
* **Solución:** Se implementó una elevación de privilegios dinámica mediante UAC que levanta un proceso PowerShell temporal con el verbo `runAs` (Ejecutar como Administrador) y aplica la directiva `-ExecutionPolicy Bypass`.

### 4. Errores de Conexión de Red en el Bot de Telegram (DNS / Timeouts)
* **Fallo:** Errores continuos de tipo `<urlopen error timed out>` u `<urlopen error [Errno 11002] getaddrinfo failed>` al intentar notificar por Telegram si la máquina se encontraba sin conexión a Internet o en suspensión. Esto hacía que el hilo se colgara o detuviera.
* **Solución:** Se envolvieron todas las llamadas de red externas en bloques `try/except` robustos en [src/notifications.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/notifications.py), de manera que se registre el fallo de comunicación en el log local, pero se continúe de forma segura sin congelar el flujo de ejecución principal.

### 5. Botón de Pedido No Encontrado en Playwright
* **Fallo:** En ocasiones se arrojaba un error de tipo `No se pudo identificar el botón o formulario de pedido de almuerzo en la página.` porque la página cambiaba dinámicamente o el selector no coincidía con las clases CSS de Angular que cambian al compilar el frontend corporativo.
* **Solución:** Se actualizó `fill_form_field` en [src/bot_engine.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/bot_engine.py) para buscar contenedores mediante patrones de texto libre (`:has-text(...)`) e inspeccionar múltiples tags alternativos (`select`, `input`, `fieldset`, `div`), garantizando compatibilidad ante cambios menores en el DOM de la aplicación web.
