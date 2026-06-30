# Proposal: Windows Desktop Application for SiGCA Lunch Automation

**Estado:** Propuesto  
**Autor:** Antigravity AI  
**Fecha:** 2026-06-18  

---

## 1. Contexto y Objetivos

El bot actual de solicitud de almuerzo automático en SiGCA (`lunch_bot.py`) funciona correctamente por línea de comandos y mediante el Programador de Tareas. Sin embargo, para mejorar la experiencia de usuario y facilitar la gestión cotidiana, el usuario requiere:
- Una interfaz gráfica de usuario (GUI) para actualizar credenciales, URLs de destino y configuraciones del bot sin editar archivos de configuración de manera directa.
- Una aplicación persistente que corra en segundo plano (System Tray) y no requiera de tareas programadas del sistema complejas de configurar.
- Notificaciones en tiempo real en la pantalla de Windows (Toast Notifications) que informen cuando se ha realizado la solicitud.
- Mensajería integrada con Telegram, tanto para avisar de ejecuciones exitosas/fallidas como para poder consultar el estado actual del bot mediante comandos (por ejemplo, enviando `/status` al bot).
- Un endpoint de verificación de salud (Health Check) local.
- Un mecanismo cómodo y visible para activar y desactivar la automatización temporalmente.

## 2. Alcance

- **Desarrollo de GUI:** Crear una ventana de configuración de escritorio con Tkinter.
- **Icono en Bandeja del Sistema:** Integrar `pystray` para que la aplicación se minimice en la bandeja del sistema al presionar cerrar, y permita reabrirse o controlarse mediante un menú contextual.
- **Hilos en segundo plano:**
  1. Hilo planificador (Scheduler) que verifica la hora local y ejecuta el bot de almuerzo una vez por día en la ventana horaria permitida.
  2. Hilo de servidor HTTP local para el Health Check en el puerto `18293`.
  3. Hilo de consulta a Telegram (polling) para responder a comandos del usuario.
- **Notificaciones:** Integrar alertas de Windows mediante PowerShell (nativo, libre de dependencias conflictivas para el compilado) o `plyer`, y notificaciones HTTP hacia la API de bots de Telegram.
- **Empaquetado:** Configurar `PyInstaller` para compilar todo el proyecto en un único ejecutable (`.exe`) autocontenido.

## 3. Limitaciones e Impacto

- **Uso de Memoria:** Al correr Playwright, la ejecución del bot consumirá temporalmente recursos de Chromium, pero el ejecutable en reposo (esperando en segundo plano) consumirá una cantidad mínima de RAM (~20-40 MB).
- **Compatibilidad de Red:** El servidor HTTP local escuchará únicamente en `127.0.0.1:18293`, lo que restringe el acceso externo para garantizar la seguridad.
- **Persistencia de Credenciales:** Seguiremos usando el archivo `.env` para almacenar credenciales locales y `config.json` para las variables de comportamiento, pero la GUI las gestionará automáticamente por debajo.
- **Requisitos de Compilación:** La compilación con `PyInstaller` requiere empaquetar los binarios de Playwright de forma correcta para que funcionen de forma autocontenida o asegurar que Playwright esté instalado en la máquina objetivo.

## 4. Plan de Mitigación y Rollback

- **Rollback:** Si la aplicación de escritorio presenta fallos, el script original `lunch_bot.py` sigue funcionando de manera independiente y puede seguir ejecutándose vía terminal o el archivo `run_job.bat`.
- **Modo Depuración:** La interfaz gráfica tendrá un botón para ver los logs en tiempo real o abrir la carpeta de evidencias y registros.
