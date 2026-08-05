---
name: error_handling_and_logging
description: Guidelines for centralized logging, GUI log redirection, error catching in Playwright web automation, Telegram alerts, and Windows Toasts.
---

# Skill: Error Handling & Logging (SiGCABot)

Esta habilidad proporciona directrices sobre cómo registrar eventos de ejecución, redirigirlos a la interfaz y tratar excepciones durante el flujo de automatización y la comunicación de alertas.

## 📝 Logging Centralizado y Redirección en GUI

El proyecto utiliza el módulo de logging estándar de Python configurado en [src/logger.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/logger.py).

### Estructura de Salidas de Logs:
1. **Archivo Físico:** Escribe los eventos detallados en [logs/lunch_automation.log](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/logs/lunch_automation.log) con codificación UTF-8.
2. **Consola:** Escribe en `sys.stdout` para depuración rápida durante desarrollo.
3. **Widget ScrolledText de la GUI (Tkinter):**
   - Implementado mediante la clase `GUILogHandler(logging.Handler)`.
   - Cuando se inicia la GUI, el handler se conecta a la ventana principal.
   - Encola la inserción de texto de manera thread-safe utilizando `widget.after(0, append_fn, msg, levelname)`.
   - Utiliza diferentes etiquetas (tags) para pintar de colores las líneas de log según su severidad (ej. rojo para errores, amarillo para advertencias).

---

## 🤖 Manejo de Errores en Web Automation (Playwright)

La interacción automatizada con sitios web corporativos debe ser altamente resiliente. Los fallos del sitio web no deben colgar el bot.

### Prácticas de Robustez en Playwright:
1. **Tolerancia a Retardos (Timeouts):** Usa `page.wait_for_selector` con timeouts prudentes (ej. 30 segundos) antes de intentar hacer clic o escribir en un campo. Captura la excepción `PlaywrightTimeoutError` de manera específica.
2. **Captura de Evidencia Fotográfica (Screenshots):** Ante cualquier fallo inesperado o excepción no controlada dentro del motor de automatización, toma una captura de pantalla del estado actual del navegador usando `capture_evidence(page, "login_error_exception")` o similar, y almacena el archivo en la carpeta [evidence/](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/evidence/).
3. **Rotación/Lista de Contraseñas:** Si la contraseña de SSO Microsoft expira o rota, el bot intenta autenticarse secuencialmente recorriendo la lista provista en `SIGCA_PASSWORDS` (separadas por comas en el `.env`). Si todas las contraseñas fallan, el bot conserva su estado activo, registra el error y envía las notificaciones configuradas. La desactivación solo puede realizarse manualmente desde la GUI.
4. **Validación de Duplicados:** Antes de rellenar el formulario de pedido, inspecciona la página web en busca de confirmaciones previas (mensajes como "Ya has solicitado almuerzo hoy" o similares). Si se detecta un registro previo, detén la operación pacíficamente indicando éxito para evitar cancelaciones erróneas o reenvíos.

---

## 🔔 Sistema de Notificaciones y Alertas

### 1. Mensajes de Telegram
- Las notificaciones se envían de forma asíncrona mediante el bot de Telegram configurado en las variables de entorno.
- **Manejo de Red Caída:** Captura excepciones de red al hacer peticiones HTTP de Telegram (ej. `urlopen error [Errno 11001] getaddrinfo failed`). Registra el error en los logs pero no bloquees la cola de ejecución.
- Si el pedido es exitoso, envía por Telegram la captura de pantalla guardada en `evidence/` como prueba irrefutable del trámite.

### 2. Notificaciones Toast de Windows
- Utiliza Windows Toast nativo (`win10toast` o llamadas de sistema) para alertar directamente en el escritorio del usuario si el bot se ejecuta localmente y ocurre un evento significativo (Éxito del pedido, Credenciales Inválidas, Error Crítico).
- Asegúrate de envolver estas llamadas en bloques `try/except` ya que los sistemas sin notificaciones habilitadas o versiones antiguas de Windows pueden lanzar excepciones.
