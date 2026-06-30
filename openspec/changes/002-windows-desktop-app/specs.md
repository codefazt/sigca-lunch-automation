# Specifications: Windows Desktop Application for SiGCA Lunch Automation

**Estado:** Propuesto  
**Versión:** 1.0.0  
**Última Actualización:** 2026-06-18  

---

## 1. Escenarios de Comportamiento (Given-When-Then)

### Escenario 1: Minimizar a la Bandeja del Sistema (System Tray)
- **GIVEN** que el usuario inicia la aplicación de escritorio (`.exe`).
- **WHEN** el usuario hace clic en el botón de cerrar (`X`) de la ventana principal.
- **THEN** la ventana principal se oculta en lugar de terminar el proceso, y un icono del bot aparece en la bandeja del sistema de Windows.
- **AND** un tooltip sobre el icono muestra `"SiGCA Bot - ACTIVO"`.

### Escenario 2: Activación y Desactivación Cómoda
- **GIVEN** que la aplicación está activa en segundo plano.
- **WHEN** el usuario hace clic derecho en el icono de la bandeja y selecciona `"Desactivar"` (o lo pulsa en la ventana de configuración).
- **THEN** la automatización se pausa (no ejecutará pedidos automáticos).
- **AND** el icono de la bandeja cambia visualmente o muestra el texto `"SiGCA Bot - INACTIVO"`.

### Escenario 3: Notificación de Pedido Exitoso
- **GIVEN** que la automatización está activa y llega la ventana horaria del pedido (ej. 15:45) y no se ha solicitado el almuerzo hoy.
- **WHEN** el hilo planificador ejecuta con éxito el bot (`lunch_bot.py`) y confirma la solicitud.
- **THEN** la aplicación envía una notificación Toast de Windows 11 con el título `"Almuerzo Solicitado"` y el texto `"El bot ha completado el pedido del almuerzo con éxito."`.
- **AND** envía un mensaje a Telegram indicando el éxito de la solicitud junto con la captura de evidencia adjunta o notificada.

### Escenario 4: Consulta de Salud (Health Check)
- **GIVEN** que la aplicación de escritorio está abierta y activa.
- **WHEN** se realiza una petición HTTP GET a `http://127.0.0.1:18293/health`.
- **THEN** el servidor responde con un estado de éxito (`200 OK`) y un JSON con la estructura:
  ```json
  {
    "status": "ok",
    "active": true,
    "last_run": "2026-06-18 15:35:10",
    "last_status": "success",
    "version": "2.0.0"
  }
  ```

### Escenario 5: Interacción por Telegram (Mensajería Bidireccional)
- **GIVEN** que la aplicación está corriendo en segundo plano.
- **WHEN** un usuario escribe `/status` o `/health` al bot de Telegram configurado.
- **THEN** el hilo poller de Telegram de la aplicación detecta el mensaje (filtrando por el `chat_id` autorizado).
- **AND** responde al chat:
  ```text
  🤖 SiGCA Bot - Estado Actual:
  - Automatización: ACTIVA ✅
  - Último pedido: 2026-06-18 15:35:10 (Éxito)
  - Próxima revisión horaria activa: Sí
  ```

---

## 2. Requisitos de la Interfaz Gráfica

- **Campos de Configuración:**
  - `SIGCA_URL`: URL del sitio.
  - `SIGCA_USER`: Correo de la cuenta corporativa.
  - `SIGCA_PASSWORDS`: Contraseñas tentativas en formato de lista (separadas por coma). Campo tipo password con botón de visibilidad (ojo).
  - `TELEGRAM_TOKEN`: Bot token del API de Telegram.
  - `TELEGRAM_CHAT_ID`: ID del chat de destino para los reportes y consultas.
  - `PREFER_MENU`: Menú favorito (Menú Saludable / Menú Estándar).
- **Acciones Directas:**
  - **Guardar:** Escribe los datos a los archivos `.env` y `config.json`.
  - **Probar Conexión Telegram:** Envía un mensaje de prueba al chat id configurado.
  - **Ejecutar Ahora (Prueba):** Corre el script en modo `--dry-run` para validar que todo conecte sin enviar un pedido real.
  - **Activar / Desactivar:** Toggle visual claro (color verde para activo, rojo para inactivo).
