# Proposal: Automatización Diaria del Pedido de Almuerzo en SiGCA

**ID del Cambio:** 001-daily-lunch-automation  
**Fecha:** 2026-06-17  
**Estado:** Propuesto  

---

## 1. Contexto y Problema
El usuario necesita realizar una solicitud diaria de almuerzo en el sistema corporativo **SiGCA** (`https://sigca.ex-cle.com/`). Este proceso manual es propenso a olvidos y está sujeto a una restricción horaria estricta: el formulario solo está habilitado desde las **4:00 PM hasta las 9:59 PM**. 

Se requiere un sistema automatizado que:
- Realice la solicitud de forma desatendida.
- Se ejecute como un Job nativo en **Windows 11**.
- Sea parametrizable (para ajustar credenciales y horarios).
- Registre detalladamente el resultado de cada intento (éxito, error, fuera de horario).

---

## 2. Alcance Propuesto

### Fase 1: Motor de Automatización (Python + Playwright)
- Desarrollo de un script en Python que interactúe con el sitio SPA en Angular.
- Flujo:
  1. Acceder a `https://sigca.ex-cle.com/`.
  2. Introducir credenciales (`johan.carmino@ex-cle.com`).
  3. Resolver inicio de sesión y cookies/sesión de Angular.
  4. Navegar a la sección de pedidos de almuerzo.
  5. Validar si el formulario está habilitado y si el almuerzo ya fue pedido para evitar duplicación.
  6. Completar el formulario y hacer clic en solicitar.
  7. Capturar captura de pantalla (screenshot) de la confirmación como evidencia visual.
  8. Guardar logs detallados en `logs/lunch_automation.log`.

### Fase 2: Configuración y Seguridad
- Archivo `.env` para almacenar credenciales:
  - `SIGCA_USER=johan.carmino@ex-cle.com`
  - `SIGCA_PASSWORD=Johan2022.`
  - `SIGCA_URL=https://sigca.ex-cle.com/`
- Archivo `config.json` para configuraciones generales de ejecución (reintentos, tiempo de espera, etc.).

### Fase 3: Integración en Windows 11 (Task Scheduler)
- Crear un script lanzador en PowerShell (`run_job.ps1`) o Batch (`run_job.bat`) que prepare el entorno virtual de Python, instale dependencias si es necesario, y ejecute el script principal.
- Instrucciones detalladas de registro del Job en el Programador de Tareas de Windows (Task Scheduler) configurado para ejecutarse diariamente a las **4:30 PM** (dentro del horario habilitado).

---

## 3. Limitaciones y Riesgos (Constraints)
- **Cambios en el HTML/Angular:** Al ser una aplicación Angular que usa bundles compilados (como `main-5APZNHYW.js`), los selectores CSS clásicos pueden cambiar tras un despliegue. Mitigaremos esto usando selectores de accesibilidad (`getByRole`, `getByText`, `getByLabel`) provistos por Playwright.
- **Doble Factor de Autenticación (MFA) o CAPTCHAs:** Si el sitio implementa CAPTCHA o verificación en dos pasos en el futuro, el script fallará. Se implementará una alerta por correo o notificación local y logs claros para detectar este caso.
- **Restricción Horaria:** El script debe verificar la hora local antes de intentar interactuar con la web para evitar bloqueos del servidor.

---

## 4. Registro de Decisiones (Decision Log)
- **Tecnología:** Python + Playwright. Playwright tiene un motor de auto-esperas superior a Selenium y funciona mejor con frameworks reactivos como Angular.
- **Persistencia:** Archivo local de log + Screenshots históricos en la carpeta `evidence/` para auditoría manual fácil.
- **Orquestador:** Windows Task Scheduler nativo, evitando dependencias externas complejas.

---

## 5. Plan de Rollback
- Si el script falla repetidamente debido a cambios estructurales en el sitio web de SiGCA, el usuario podrá desactivar la Tarea Programada en Windows y realizar el pedido manualmente hasta que el script se actualice con los nuevos selectores.
