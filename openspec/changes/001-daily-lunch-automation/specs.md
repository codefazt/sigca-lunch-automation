# Specs: Criterios de Aceptación y Escenarios de Prueba (BDD)

**ID del Cambio:** 001-daily-lunch-automation  
**Fecha:** 2026-06-17  
**Estado:** Propuesto  

Este documento define el comportamiento esperado del sistema mediante especificaciones ejecutables en formato **Given / When / Then**.

---

## Escenario 1: Flujo Exitoso (Camino Feliz)
**Given** que la hora actual está dentro del rango permitido (4:00 PM - 9:59 PM)  
**And** el script tiene credenciales correctas en el archivo `.env`  
**And** el usuario aún no ha pedido almuerzo para el día siguiente  
**When** el job se ejecuta automáticamente  
**Then** el script debe abrir el navegador headless  
**And** iniciar sesión en `https://sigca.ex-cle.com/` correctamente  
**And** navegar al formulario de solicitud de almuerzo  
**And** seleccionar la opción de almuerzo disponible  
**And** confirmar el pedido de almuerzo  
**And** tomar una captura de pantalla del mensaje de éxito y guardarla en `evidence/YYYY-MM-DD_success.png`  
**And** escribir un registro en `logs/lunch_automation.log` con nivel `INFO: Pedido realizado con éxito.`  

---

## Escenario 2: Intento Fuera de Horario
**Given** que la hora actual está fuera del rango permitido (por ejemplo, 10:00 AM)  
**When** el job es ejecutado por error o manualmente  
**Then** el script debe registrar en `logs/lunch_automation.log` con nivel `WARNING: Intento de ejecución fuera de horario (4:00 PM - 9:59 PM). Terminando ejecución.`  
**And** cerrarse inmediatamente sin abrir el navegador para ahorrar recursos.

---

## Escenario 3: Almuerzo ya Solicitado Previamente
**Given** que el usuario ya ha solicitado el almuerzo con anterioridad  
**When** el script navega al formulario de solicitud  
**Then** debe identificar que el botón o el estado de la solicitud indica "Solicitado" o similar  
**And** no debe intentar hacer un nuevo envío para evitar comportamientos inesperados  
**And** registrar en los logs `INFO: El almuerzo ya había sido solicitado anteriormente para este día.`  
**And** guardar una captura de pantalla del estado actual en `evidence/YYYY-MM-DD_already_ordered.png`.

---

## Escenario 4: Credenciales Incorrectas
**Given** que el usuario o contraseña en el archivo `.env` son incorrectos o expiraron  
**When** el script intenta iniciar sesión  
**Then** debe identificar el mensaje de error de inicio de sesión en la pantalla de login  
**And** registrar una entrada en los logs `ERROR: Fallo de autenticación. Credenciales inválidas.`  
**And** guardar una captura de pantalla en `evidence/YYYY-MM-DD_auth_error.png`  
**And** terminar con un código de error de salida `1` para reportar la falla al programador de tareas.

---

## Escenario 5: Servidor Caído / Sin Conectividad
**Given** que la web `https://sigca.ex-cle.com/` no responde o da un error 5xx  
**When** el script intenta acceder al sitio  
**Then** Playwright debe reintentar la conexión un número máximo de veces configurado (por ejemplo, 3 reintentos)  
**And** si falla finalmente, registrar `ERROR: No se pudo conectar a la plataforma SiGCA tras 3 intentos.`  
**And** guardar el log de error y salir con código `2`.
