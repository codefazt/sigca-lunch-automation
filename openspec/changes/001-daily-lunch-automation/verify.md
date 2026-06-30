# Verify: Plan de Verificación y Evidencia de Pruebas

**ID del Cambio:** 001-daily-lunch-automation  
**Fecha:** 2026-06-17  
**Estado:** Propuesto  

Este documento describe cómo se verifica que el bot de almuerzo cumple con los requisitos y funciona de manera confiable.

---

## 1. Pruebas Automatizadas (TDD)

Las pruebas unitarias y de integración se ejecutan localmente con `pytest`.

### Comando de ejecución:
```bash
# Activar entorno virtual y ejecutar pruebas
venv\Scripts\activate
pytest -v tests/
```

### Resultados esperados:
- `test_is_time_valid_during_window`: Debe pasar con éxito al ingresar horas entre 4:00 PM y 9:59 PM.
- `test_is_time_valid_outside_window`: Debe pasar indicando falsedad al probar horas fuera de la ventana.
- `test_missing_env_variables`: Debe lanzar una excepción controlada del tipo `ValueError`.

---

## 2. Pruebas de Integración y de Humo (Dry Run)

### Simulación de ejecución real
Se ejecuta el script con el navegador en modo no-headless para ver la interacción (o guardando screenshots si es headless).

### Comando de ejecución:
```bash
python lunch_bot.py --dry-run
```
*(Nota: El parámetro `--dry-run` permite simular el inicio de sesión y la navegación sin llegar a pulsar el botón final de confirmar almuerzo, para no realizar pedidos reales durante las pruebas).*

---

## 3. Evidencia Manual Requerida

### Logs
Comprobar que el archivo `logs/lunch_automation.log` contenga líneas con el formato:
```text
YYYY-MM-DD HH:MM:SS - INFO - Inicializando LunchBot...
YYYY-MM-DD HH:MM:SS - INFO - Comprobando rango de horas. Hora actual válida.
YYYY-MM-DD HH:MM:SS - INFO - Iniciando sesión para johan.carmino@ex-cle.com...
YYYY-MM-DD HH:MM:SS - INFO - Login exitoso. Navegando al menú.
...
```

### Capturas de Pantalla (Screenshots)
Verificar que la carpeta `evidence/` contenga capturas legibles que muestren:
1. El login completado.
2. El estado del menú de almuerzos (ej. almuerzo solicitado o botón de solicitud).

---

## 4. Auditoría del Job de Windows 11
En el Programador de Tareas (Task Scheduler):
1. Seleccionar la tarea `SiGCA Auto Lunch Order`.
2. Hacer clic en "Run" (Ejecutar) de manera manual.
3. Verificar en la pestaña "History" (Historial) que el código de resultado final (Last Run Result) sea `0x0` (Éxito).
4. Comprobar que se ha añadido un nuevo registro en `logs/lunch_automation.log` y una captura de pantalla en `evidence/`.
