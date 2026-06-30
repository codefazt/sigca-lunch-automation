# Verification: Windows Desktop Application for SiGCA Lunch Automation

**Estado:** Propuesto  
**Versión:** 1.0.0  
**Última Actualización:** 2026-06-18  

---

## 1. Pruebas de Funcionamiento Local (Desarrollo)

Para validar cada componente durante el desarrollo, realizaremos las siguientes verificaciones:

### A. Prueba de Notificaciones
- **Acción:** Ejecutar un script de prueba que dispare una notificación Toast de Windows y un mensaje de Telegram.
- **Resultado Esperado:**
  - El sistema operativo Windows muestra un Toast Banner con el mensaje configurado.
  - El canal/chat de Telegram recibe el mensaje con marca de tiempo del bot de forma instantánea.

### B. Servidor de Health Check
- **Acción:** Levantar el servidor HTTP y realizar las siguientes llamadas desde un navegador o cliente HTTP local:
  - `curl http://127.0.0.1:18293/health`
  - `curl http://127.0.0.1:18293/`
- **Resultado Esperado:**
  - `/health` devuelve JSON válido `{"status": "ok", ...}` y código HTTP `200 OK`.
  - `/` carga una página web HTML estilizada con la información de logs y evidencias correspondientes.

### C. Bandeja del Sistema e Interfaz
- **Acción:** Arrancar `app_gui.py`, cerrar la ventana, comprobar que sigue en segundo plano, interactuar con el menú contextual de la bandeja de sistema.
- **Resultado Esperado:**
  - Al cerrar la ventana, esta desaparece de la pantalla pero el proceso sigue vivo en el Administrador de tareas.
  - Al hacer clic derecho en la bandeja y pulsar "Abrir Configuración", la ventana se vuelve a mostrar con los datos intactos.
  - Al alternar el estado a "Inactivo" desde el menú tray, el estado del bot cambia y no ejecuta el planificador.

---

## 2. Pruebas de Compilación y Distribución

### Compilado (.exe)
- **Acción:** Ejecutar el comando de `pyinstaller` y arrancar el ejecutable generado en `dist/SiGCABot.exe`.
- **Resultado Esperado:**
  - El archivo se compila sin errores.
  - El ejecutable inicia sin abrir una ventana de consola negra persistente (`--noconsole`).
  - La aplicación inicia correctamente en segundo plano y lee los archivos `.env` y `config.json` relativos a su ruta de ejecución.
  - El consumo de memoria se mantiene en niveles óptimos durante la inactividad.
