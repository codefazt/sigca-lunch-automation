# Specification: Solicitud Automática de Almuerzo (SiGCA)

**Estado:** Activo  
**Versión:** 1.1.0  
**Última Actualización:** 2026-06-17  

Este documento describe la especificación técnica y funcional permanente para el Job automatizado de solicitud de almuerzo corporativo en **SiGCA**.

---

## 1. Comportamiento Esperado (Specs Funcionales)

1.  **Validación de Ventana Horaria (Spanning Midnight):**
    *   El bot solo debe proceder si la hora de ejecución local se encuentra dentro de la ventana de **3:30 PM (15:30) a 9:59 AM**.
    *   Al cruzar la medianoche, se considera válida si es `>= 15:30` o `< 10:00`.
    *   Si se ejecuta fuera de este horario, escribe un Warning en los logs y termina sin interactuar con la web.

2.  **Autenticación de Usuario (Microsoft SSO):**
    *   El bot debe ingresar al sitio `https://sigca.ex-cle.com/`.
    *   Debe detectar y hacer clic en el botón de **Continuar con Microsoft**.
    *   Debe rellenar secuencialmente el correo del usuario (`SIGCA_USER`) y la contraseña.
    *   En caso de fallo en el inicio de sesión, debe reintentar con las contraseñas alternativas configuradas en `SIGCA_PASSWORDS` (separadas por comas).
    *   Debe responder afirmativamente/omitir el diálogo de Microsoft "¿Mantener la sesión iniciada?".
    *   Los fallos de autenticación deben registrarse y notificarse sin cambiar `is_active`; el usuario es el único que puede desactivar el bot desde la GUI.

3.  **Comprobación de Estado Previo:**
    *   Una vez dentro del módulo "Almuerzo", el bot debe validar si ya existe una solicitud registrada para el día (buscando textos como `"Solicitud registrada"` o `"Has realizado tu solicitud"`).
    *   Si ya está solicitado, no debe re-enviar el formulario y salir con código `0` de éxito.

4.  **Selección de Menú:**
    *   Debe leer la preferencia del usuario en `config.json` (`"prefer_menu": "saludable"` o `"estandar"`).
    *   Debe intentar hacer clic en la opción del menú correspondiente a su preferencia (buscando textos como `"Saludable"` o `"Estándar"`). Si no está disponible, debe hacer clic en la opción alternativa como plan de respaldo.

5.  **Llenado de Formulario Adicional (Evaluaciones/Preguntas 1 a 7):**
    *   Dado que las preguntas son condicionales y a veces no se muestran todas, el bot debe validar de forma dinámica qué campos existen en la página y rellenar únicamente los que estén presentes:
        *   **Q1: Ubicación:** Selecciona la opción `"Sede ExCle"`.
        *   **Q2: De 1 a 5 estrellas:** Selecciona el botón de opción única (radio) `"3"`.
        *   **Q3: ¿Alimentos bien cocidos?:** Selecciona la última opción del selector (`"Les faltaba cocción"`).
        *   **Q4: ¿Porción acorde?:** Selecciona la última opción del selector (`"Poca comida"`).
        *   **Q5: Condimentación:** Selecciona la primera opción de datos tras la de por defecto (índice 1: `"Tenía el condimento justo / plato equilibrado"`).
        *   **Q6: ¿Asistir después de las 01:30 PM?:** Selecciona el radio button `"Si"` / `"Sí"`.
        *   **Q7: Comentario:** Rellena el textarea con: `"Favor quitar el jugo de melon y las porciones no tienen suficiente proteina, quedando uno con hambre"`.

6.  **Envío del Formulario:**
    *   Debe hacer clic en el botón de confirmación (`"Solicitar"`, `"Pedir Almuerzo"`, `"Enviar"`, etc.).
    *   Debe capturar una captura de pantalla final como evidencia física del pedido exitoso.
    *   Si el mensaje posterior al envío no se confirma, el resultado debe tratarse como no confirmado y no como éxito.

---

## 2. Parámetros de Configuración

### Archivo `.env` (Variables locales privadas)
```bash
SIGCA_USER=johan.carmino@ex-cle.com
SIGCA_PASSWORDS=Contraseña1,Contraseña2
SIGCA_URL=https://sigca.ex-cle.com/
```

### Archivo `config.json` (Parámetros del bot)
```json
{
  "start_hour": 15,
  "start_minute": 30,
  "end_hour": 10,
  "end_minute": 0,
  "timeout_ms": 30000,
  "headless": true,
  "retries": 3,
  "retry_delay_sec": 300,
  "retry_attempt_delay_sec": 5,
  "prefer_menu": "saludable"
}
```

---

## 3. Arquitectura del Job y Programador de Tareas

El script se ejecuta diariamente bajo la utilidad del Programador de Tareas de Windows:
*   **Archivo ejecutor:** `run_job.bat` (Encargado de inicializar el entorno `venv`, verificar dependencias y arrancar `app_gui.py --run-job`, que valida y persiste `status.json`).
*   **Programación:** Todos los días a la hora de inicio configurada, de forma invisible en segundo plano.
*   **Logs históricos:** Guardados en `logs/lunch_automation.log`.
*   **Capturas de pantalla de evidencia:** Guardadas con marca de tiempo en `evidence/`.
