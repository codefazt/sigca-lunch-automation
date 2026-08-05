# Registro de Tarea en el Programador de Tareas de Windows 11

Este documento detalla cómo programar la ejecución automática del bot de almuerzo todos los días a una hora específica utilizando el Programador de Tareas de Windows (Task Scheduler).

---

## Opción 1: Registro desde la Interfaz Gráfica de SiGCABot (Recomendado)

La forma más sencilla de registrar la tarea es directamente desde la aplicación:

1. Abre **SiGCABot** (ya sea `SiGCABot.exe` o `python app_gui.py`).
2. Ve a la pestaña **Configuración**.
3. Configura la **hora de revisión** deseada (Hora:Minuto) en la sección de ajustes.
4. Localiza la sección **Programador de Tareas de Windows**.
5. Haz clic en el botón **📋 Registrar Tarea Diaria**.
6. Windows te solicitará una **confirmación de permisos de Administrador** (diálogo UAC). Haz clic en **Sí**.
7. La etiqueta de estado cambiará a **✅ Tarea registrada en Windows**.

> [!NOTE]
> La aplicación detecta automáticamente si corre como ejecutable compilado (`.exe`) o desde código fuente, y registra la tarea con la ruta dinámica correspondiente.
> - **Compilado:** La tarea apunta a `SiGCABot.exe --run-job`.
> - **Desarrollo:** La tarea apunta a `run_job.bat`, que delega en `app_gui.py --run-job` para aplicar las validaciones de estado y actualizar `status.json`.

La tarea registrada desde la GUI se repite cada 1 hora durante 18 horas. El bot evita nuevas solicitudes mediante `status.json`, la detección de duplicados en SiGCA y un bloqueo compartido entre procesos.

Para **eliminar** la tarea, haz clic en **🗑️ Eliminar Tarea** (también requiere permiso de Administrador).

---

## Opción 2: Registro Rápido mediante PowerShell

Si prefieres registrar la tarea manualmente, abre una terminal de **PowerShell con privilegios de Administrador** y ejecuta:

### Desde el ejecutable compilado (.exe):
```powershell
$exePath = "RUTA\AL\SiGCABot.exe"
$action = New-ScheduledTaskAction -Execute $exePath -Argument "--run-job" -WorkingDirectory (Split-Path $exePath)
$trigger = New-ScheduledTaskTrigger -Daily -At 4:30PM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 0
Register-ScheduledTask -TaskName "SiGCA Auto Lunch Order" -Trigger $trigger -Action $action -Settings $settings -Description "Job automático diario para solicitar almuerzo en SiGCA" -Force
```

### Desde el código fuente (desarrollo):
```powershell
$batPath = "RUTA\AL\PROYECTO\run_job.bat"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $batPath + '"') -WorkingDirectory (Split-Path $batPath)
$trigger = New-ScheduledTaskTrigger -Daily -At 4:30PM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 0
Register-ScheduledTask -TaskName "SiGCA Auto Lunch Order" -Trigger $trigger -Action $action -Settings $settings -Description "Job automático diario para solicitar almuerzo en SiGCA" -Force
```

> [!IMPORTANT]
> Reemplaza `RUTA\AL\...` con la ruta absoluta real a tu ejecutable o archivo batch. Si usas la **Opción 1** (desde la GUI), la ruta se calcula automáticamente.
> La tarea utiliza un disparo diario a la hora configurada y repeticiones horarias durante 18 horas. `retry_delay_sec` pertenece al planificador interno de la GUI; la espera entre intentos del navegador se controla con `retry_attempt_delay_sec`.

---

## Opción 3: Registro Manual usando la Interfaz Gráfica de Windows

Si prefieres usar la interfaz visual de Windows:

1. Presiona `Win + R`, escribe `taskschd.msc` y presiona **Enter** para abrir el **Programador de Tareas**.
2. En el panel lateral derecho, selecciona **Crear tarea básica...** (Create Basic Task):
   - **Nombre:** `SiGCA Auto Lunch Order`
   - **Descripción:** `Job automático para solicitar almuerzo de forma diaria en SiGCA.`
   - Haz clic en **Siguiente**.
3. **Desencadenador (Trigger):**
   - Selecciona **Diariamente** (Daily).
   - Configura la fecha de inicio y hora: **16:30:00** (4:30 PM).
   - Recurrencia: cada **1** día.
   - Haz clic en **Siguiente**.
4. **Acción:**
   - Selecciona **Iniciar un programa** (Start a program).
   - **Programa/script:** Ruta a `SiGCABot.exe` o `run_job.bat`
   - **Argumentos (si usas .exe):** `--run-job`
   - **Iniciar en (opcional):** Directorio donde se encuentra el ejecutable.
   - Haz clic en **Siguiente**.
5. Revisa el resumen y marca la casilla **Abrir el diálogo Propiedades para esta tarea al hacer clic en Finalizar**.
6. En el diálogo de **Propiedades de la tarea**:
   - En la pestaña **General**:
     - Selecciona **Ejecutar tanto si el usuario inició sesión como si no** (Run whether user is logged on or not).
     - Marca la casilla **Ejecutar con los privilegios más altos** (Run with highest privileges).
   - En la pestaña **Configuración** (Settings):
     - Marca **Detener la tarea si se ejecuta durante más de:** `1 hora`.
      - No configurar reinicios adicionales de la tarea. El motor gestiona sus reintentos y la tarea se repite cada hora durante la ventana configurada.
   - Haz clic en **Aceptar**. Te solicitará la contraseña de tu usuario de Windows.

---

## Verificación de Funcionamiento

Para validar que la tarea funciona:
1. Localiza la tarea `SiGCA Auto Lunch Order` en la biblioteca del Programador de Tareas (`taskschd.msc`).
2. Haz clic derecho sobre ella y selecciona **Ejecutar** (Run).
3. Revisa el archivo de log en `logs/lunch_automation.log` y verifica si se creó un nuevo registro de ejecución.
4. Revisa la carpeta `evidence/` para ver las capturas de pantalla creadas durante la ejecución.
