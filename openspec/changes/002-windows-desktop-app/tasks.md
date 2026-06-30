# Tasks: Windows Desktop Application for SiGCA Lunch Automation

Este checklist guía el proceso de implementación bajo la metodología Gentleman AI.

---

## Fase 1: Entorno y Dependencias
- [ ] Instalar dependencias necesarias en el entorno virtual (`venv`):
  - `pystray` para el icono en la bandeja del sistema.
  - `Pillow` para procesamiento y visualización de imágenes (iconos).
  - `pyinstaller` para la compilación final.
- [ ] Probar la instalación de las dependencias importándolas en un archivo de prueba.

## Fase 2: Módulos de Notificación e Integración
- [ ] Implementar la función de envío de notificaciones de Telegram mediante `urllib.request` en `lunch_bot.py`.
- [ ] Implementar la función de envío de notificaciones Toast de Windows usando un comando subprocess de PowerShell en `lunch_bot.py`.
- [ ] Crear el hilo poller de Telegram que escuche mensajes `/status` y `/health` y responda adecuadamente.

## Fase 3: Servidor de Health Check Local
- [ ] Desarrollar la clase del servidor HTTP basada en `http.server.BaseHTTPRequestHandler`.
- [ ] Implementar el endpoint `/health` que retorne el estado actual de la automatización en formato JSON.
- [ ] Implementar la vista del dashboard HTML en `/` con logs actualizados y previsualización de capturas de evidencias.
- [ ] Levantar el servidor en un puerto libre configurado (por defecto `18293`) en un hilo secundario de la app principal.

## Fase 4: Planificador en Segundo Plano (Scheduler)
- [ ] Desarrollar el loop infinito en segundo plano que despierte cada 60 segundos.
- [ ] Validar contra `status.json` si ya se ha realizado con éxito el pedido de almuerzo hoy.
- [ ] Si la automatización está activa (`is_active: true`) y está dentro de la ventana horaria válida, iniciar la rutina del bot.

## Fase 5: Interfaz de Usuario y System Tray
- [ ] Diseñar la ventana de Tkinter con estilos oscuros y limpios.
- [ ] Agregar los controles de entrada para todas las variables de configuración y el toggle visual de habilitado/deshabilitado.
- [ ] Añadir botones para probar la conexión de Telegram y realizar un test rápido en seco (`--dry-run`).
- [ ] Integrar `pystray` para que oculte y muestre la interfaz de usuario en segundo plano y asocie el menú contextual de control rápido.

## Fase 6: Compilación y Verificación
- [ ] Validar todo el flujo de extremo a extremo de forma local.
- [ ] Compilar la aplicación con `PyInstaller` generando el archivo `SiGCABot.exe`.
- [ ] Probar que el archivo `.exe` compilado se ejecute correctamente en Windows 11 y realice el ciclo de vida completo.
