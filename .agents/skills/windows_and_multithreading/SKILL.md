---
name: windows_and_multithreading
description: Technical guidelines for thread safety, GUI event loop integration, Windows Registry, Task Scheduler, and Playwright execution paths.
---

# Skill: Windows & Multithreading (SiGCABot)

Esta habilidad documenta las prácticas para programar en entornos multihilo en Python con interfaces Tkinter, y las integraciones específicas del sistema operativo Windows.

## 🧵 Modelo Multihilo y Thread Safety en Tkinter

Tkinter no es seguro para accesos concurrentes desde múltiples hilos. Si un hilo secundario intenta modificar directamente un widget de Tkinter (por ejemplo, cambiar el texto de un Label o insertar líneas en un ScrolledText), la aplicación puede congelarse, mostrar corrupción gráfica o fallar críticamente.

### Reglas de Multihilo:
1. **Hilo Principal (GUI Thread):** Ejecuta `root.mainloop()`. Responde a las interacciones de entrada del usuario y actualiza los componentes visuales.
2. **Hilos Secundarios (Worker Threads):** Realizan tareas pesadas:
   - Hilo Planificador (`scheduler.py` loop).
   - Hilo del Servidor HTTP (`health_server.py`).
   - Hilo de actualización de Telegram (`telegram_poller.py`).
   - Hilo de ejecución temporal (cuando el usuario presiona "Simular Pedido", se crea un hilo para evitar congelar el botón).
3. **Comunicación Segura hacia la GUI:** Para interactuar con la GUI desde un hilo secundario, utiliza el método `.after(delay_ms, callback, *args)` de Tkinter. Esto encola el callback para ser ejecutado de forma segura por el hilo de la GUI tan pronto como esté libre.
   ```python
   # Ejemplo correcto de actualización de estado
   def update_gui_status_badge():
       if app:
           app.root.after(0, _update_gui_status_badge_sync)
   ```
4. **Finalización de Hilos (Graceful Shutdown):** Para terminar todos los bucles infinitos (`while True`) de los hilos de background al cerrar la ventana, se debe leer la variable compartida `state.stop_threads`.
   - Antes de cerrar la ventana principal o el system tray, pon `state.stop_threads = True` y detén los servidores/pollers.

---

## 🪟 Integraciones del Sistema Windows

### 1. Ocultar Ventanas de Consola
Cuando el bot corre empaquetado como ejecutable `.exe` por PyInstaller, no queremos que se abra una ventana de comandos en negro de fondo.
- El módulo [src/config.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/config.py) utiliza `ctypes.windll.kernel32.GetConsoleWindow()` y `ShowWindow(hwnd, 0)` para ocultar la ventana en modo GUI de manera dinámica.

### 2. Registro de Auto-Inicio en Windows
Para configurar el inicio automático con el encendido de la computadora, se modifica el registro de Windows de la sesión de usuario:
- Ruta de registro: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
- Nombre de la clave: `SiGCALunchBot`
- El valor contiene la ruta absoluta al ejecutable o script python con sus respectivos argumentos de inicio oculto.

### 3. Programador de Tareas de Windows (Task Scheduler)
Para configurar ejecuciones automatizadas confiables a horas fijas (incluso con la aplicación cerrada):
- Se usa PowerShell desde Python mediante `subprocess` con privilegios elevados de UAC para registrar la tarea.
- Debido a la complejidad de las comillas y caracteres en comandos largos de PowerShell, los comandos se construyen en Python, se codifican en Base64 con codificación UTF-16LE, y se pasan al parámetro `-EncodedCommand` de PowerShell.
- Esto evita problemas de sintaxis y permite pasar argumentos y configuraciones complejas directamente al planificador.

### 4. Ruta de Navegadores Playwright
En Windows, cuando una tarea es programada e iniciada por el sistema (ej. bajo el usuario `SYSTEM` u otra cuenta administrativa), la ruta por defecto del perfil de usuario cambia a `C:\WINDOWS\system32\config\systemprofile`.
- **Fallo Común:** Playwright no encuentra la instalación de Chromium allí y falla con `BrowserType.launch: Executable doesn't exist`.
- **Solución:** Forzar explícitamente a Playwright a usar el directorio de navegadores compartidos del usuario en AppData local definiendo la variable de entorno al arrancar el motor:
  ```python
  os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
      os.path.expanduser("~"), "AppData", "Local", "ms-playwright"
  )
  ```
