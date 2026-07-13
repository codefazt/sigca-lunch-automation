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

### 6. Manual Integrado y Documentación Web (Versión 2.3.0)
- **Manual Visual paso a paso (GUI):** Pestaña "Manual de Uso" integrada con scroll fluido, que contiene explicaciones detalladas y capturas de cada sección de la aplicación (`images_info/`).
- **Documentación Extensa Web:** Endpoint HTTP `/manual` que sirve una interfaz oscura premium con Outfit/Inter font, que documenta de manera integral el bot, las variables `.env`, config.json y reintentos automáticos.
- **Ruta de Recursos `/images_info`:** Endpoint HTTP seguro en el health check local que sirve recursos estáticos para la documentación en el navegador de manera controlada con `os.path.basename` (previniendo path traversal).
- **Compilación de Activos:** Modificación de `SiGCABot.spec` y `build.bat` para asegurar que el directorio `images_info` esté completamente empaquetado tanto dentro de la estructura de recursos internos (`sys._MEIPASS`) como físicamente en el directorio portable.

### 7. Directrices Estéticas para Notificaciones y Modales
- **Prohibición de Ventanas Nativas:** Prohibido el uso de diálogos messagebox de Tkinter nativos (grises y asimétricos).
- **Modales Premium Integrados:** Implementación del estilo Catppuccin para notificaciones internas de primer plano con un borde de `2px` que indica severidad (`ACCENT_BLUE` para información, `ACCENT_GREEN` para éxito, `ACCENT_YELLOW` para alertas, `ACCENT_RED` para errores) e interactividad con efectos hover dinámicos en los botones.
- **Notificaciones Toast Windows:** Los Toasts se reservan para notificaciones en segundo plano, siempre envueltos en bloques robustos de excepciones.

### 8. Optimizaciones, Seguridad y Cuestionario Dinámico
- 🎯 Hitos Recientes Completados:
1. **Verificación de Dependencias y Auto-Reparación (v2.2.0):** Implementación de una rutina ligera de inicio que comprueba la existencia de Chromium y dependencias en un máximo de 8 segundos. En caso de fallos (C++ DLLs faltantes, Antivirus o navegador no instalado), lanza un modal interactivo para descargar o instalar automáticamente los componentes necesarios sin que la app crashee.
2. **Ejecución Fuera de Proceso (Subprocesos):** Desacoplamiento de las rutinas de Playwright (Dry Run, Solicitud Manual y Cancelación) del proceso principal mediante `subprocess.Popen`. Esto erradica los bloqueos (deadlocks) en Tkinter y libera la memoria de forma garantizada tras la finalización, ya que el sistema operativo mata físicamente los procesos Chromium/Node (con limpieza forzada tras timeout de 30s).
3. **Botón de Parada Forzada:** Implementación de un botón de aborto en el panel lateral que detiene inmediatamente el subproceso actual e invoca la limpieza de cualquier proceso huérfano de Playwright.
4. **Cuestionario Dinámico (v2.1.0):** Los usuarios pueden definir las respuestas fijas a las preguntas dinámicas de ubicación, guarnición, nivel de cocción, etc., directamente desde una pestaña "Cuestionario" en la GUI, persistiendo en `config.json`.
5. **Encriptación Segura de Credenciales:** En lugar de guardar la contraseña en texto plano en la GUI, ahora se aplica una ofuscación base64 (reversible) en `.env` para añadir una capa adicional de protección frente a mirones.
6. **Notificaciones Asíncronas e Hilos Separados:**
   - La subida de capturas y envío de mensajes a Telegram ahora corren asíncronamente.
   - Tkinter maneja todas las llamadas UI usando colas y variables compartidas (`app_gui.py` desacoplado de la lógica bloqueante).
7. **Resolución de Error de Consola en Windows (.exe):** Se configuró explícitamente `encoding='utf-8'` y manejo de excepciones en todos los comandos de stdout para que el empaquetado `console=False` no crashee en sistemas Windows en español (cp1252).

### 9. Tarea Programada Repetitiva, Fechas Amigables y Notificaciones Saneadas (Versión 2.4.6)
- **Hitos Completados:**
  1. **Disparo Repetitivo Horario:** Configuración automática en el Programador de Windows para que la tarea diaria se repita cada 1 hora por 18 horas, logrando robustez ante apagados de la máquina o suspensión.
  2. **Validación al Registrar:** Al crear la tarea por primera vez o re-registrarla, la GUI detecta si está en rango de solicitud para lanzar una petición asíncrona de fondo inmediatamente o notificar que está fuera de rango pero programada.
  3. **Sanitización Multilínea de Logs en Popups:** Limpieza centralizada de timestamps (`YYYY-MM-DD HH:MM:SS,mmm`), niveles `[INFO]` y códigos técnicos de salida `(código: 0)` en los diálogos emergentes, presentando al usuario final un diseño libre de tecnicismos.
  4. **Fecha Amigable en Español:** Conversión de marcas de tiempo a un formato legible y estético (ej. `13 de Julio, 11:28 AM`) en la barra lateral del aplicativo y en los modales de éxito.

### 10. Robustez en Cancelación con Reintentos Incrementales (Versión 2.4.7)
- **Hitos Completados:**
  1. **Bucle de 3 Intentos:** Envoltura del proceso de cancelación en un bucle que realiza hasta 3 intentos en caso de lentitud o fallos temporales en la carga de la página.
  2. **Timeouts Incrementales:** Aplicación de multiplicadores (1.0, 1.5, y 2.0) al timeout de la página y retrasos de navegación según el intento, aumentando las probabilidades de éxito.
  3. **Notificaciones Consolidadas:** Silenciado de alertas Toast y Telegram en intentos fallidos intermedios, enviando únicamente la notificación final correspondiente (éxito o fallo definitivo).

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
* **Solución:** Se actualizó `fill_form_field` en `src/bot_engine.py` para buscar contenedores mediante patrones de texto libre (`:has-text(...)`) e inspeccionar múltiples tags alternativos (`select`, `input`, `fieldset`, `div`), garantizando compatibilidad ante cambios menores en el DOM de la aplicación web.

### 6. Congelamiento por Modales (Deadlock en Tkinter)
* **Fallo:** La GUI se congelaba (deadlock) y no respondía al pulsar botones que lanzaban modales debido al uso de `self.wait_window()` en el constructor de `PremiumMessageBox` y `PremiumConfirmBox`.
* **Solución:** Se removió `self.wait_window()` de los constructores y se delegó la responsabilidad al llamador externo, evitando bloquear el bucle principal de eventos.

### 7. Error del Codificador 'charmap' de Windows (Emojis)
* **Fallo:** El registro de eventos con emojis generaba `UnicodeEncodeError` en la consola de Windows (que usa codificación CP1252), provocando el colapso de la aplicación.
* **Solución:** Se forzó a `sys.stdout` y `sys.stderr` a usar codificación UTF-8 con la política de reemplazo `errors="backslashreplace"` para imprimir emojis y caracteres especiales de forma segura.

### 8. Error de Propiedad 'Interval' al Configurar Trigger Diario en PowerShell 5.1
* **Fallo:** Al registrar la tarea programada repetitiva mediante PowerShell 5.1 en Windows 10/11, la asignación de repetición `$trigger.Repetition.Interval = 'PT1H'` fallaba con `PropertyNotFound` porque `New-ScheduledTaskTrigger -Daily` no expone de forma activa el objeto de repetición CIM.
* **Solución:** Se utilizó un trigger temporal `-Once` (que sí tiene el objeto `Repetition` instanciado por defecto) y se le copió su configuración de repetición al trigger `-Daily`:
  ```powershell
  $trigger = New-ScheduledTaskTrigger -Daily -At '{trigger_time}'
  $tempTrigger = New-ScheduledTaskTrigger -Once -At '{trigger_time}' -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Hours 18)
  $trigger.Repetition = $tempTrigger.Repetition
  ```

### 9. Fallo en Cancelación de Solicitud por Lentitud de Red (Intento Único)
* **Fallo:** La rutina de cancelación realizaba un solo intento. Si la red corporativa o la carga de la página sufrían una ralentización temporal, la cancelación fallaba inmediatamente y spameaba notificaciones fallidas a Telegram y Toast locales.
* **Solución:** Se envolvió el flujo en un bucle de hasta 3 intentos con timeouts y retrasos progresivamente mayores (factor 1.0, 1.5, y 2.0). Se silenciaron las alertas para los primeros dos intentos fallidos y se retrasaron hasta tener una respuesta final o agotar los intentos.
