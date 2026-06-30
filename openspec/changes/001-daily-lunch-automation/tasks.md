# Tasks: Lista de Tareas para la Implementación (TDD)

**ID del Cambio:** 001-daily-lunch-automation  
**Fecha:** 2026-06-17  
**Estado:** Propuesto  

---

## 1. Configuración del Entorno de Desarrollo
- [ ] Crear el archivo `.gitignore` para omitir `venv/`, `__pycache__/`, `.env` y logs.
- [ ] Crear el archivo `requirements.txt` con las dependencias necesarias:
  - `playwright`
  - `python-dotenv`
  - `pytest`
- [ ] Crear el archivo `.env.template` como plantilla explicativa para el usuario.
- [ ] Crear el archivo `config.json` con los parámetros iniciales de tiempo y reintentos.

---

## 2. Desarrollo del Bot en Modo Strict TDD (Tests Primero)
- [ ] Crear el archivo de pruebas `tests/test_lunch_bot.py` para definir los escenarios de prueba:
  - Validar rango de horas locales (éxito dentro de la ventana, error fuera).
  - Validar comportamiento ante la falta de variables de entorno (debe lanzar error controlado).
  - Mockear el navegador para simular el inicio de sesión y comprobar códigos de retorno.
- [ ] Implementar la clase `LunchBot` en `lunch_bot.py`:
  - Lógica de carga de configuración y validación horaria.
  - Inicialización y configuración del navegador en modo headless.
  - Implementación del flujo de navegación y selectores de login.
  - Implementación del flujo de validación de almuerzo ya pedido y selección de plato.
  - Lógica de captura de screenshots y escritura en archivos de logs.

---

## 3. Scripts de Orquestación e Integración de Windows
- [ ] Crear el script ejecutor por lotes `run_job.bat`.
- [ ] Documentar en un archivo `WINDOWS_SCHEDULER.md` los comandos de PowerShell para registrar el Job automáticamente, o los pasos detallados de la interfaz gráfica de Windows.

---

## 4. Verificación
- [ ] Ejecutar la suite de pruebas locales (`pytest`) y verificar que todos los casos (happy path y excepciones) pasen.
- [ ] Realizar una ejecución manual "Dry Run" (en modo visible o headless con screenshot) del script para validar la conectividad real con `https://sigca.ex-cle.com/`.
