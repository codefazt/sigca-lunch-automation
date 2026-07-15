"""
Motor de automatización web de SiGCABot.
Contiene la clase LunchBot con toda la lógica de Playwright para:
- Inicio de sesión (SSO Microsoft + formulario estándar)
- Navegación a la sección de almuerzos
- Selección de menú y llenado de formulario
- Captura de evidencias (screenshots)
- Cancelación de pedidos
"""

import os
import sys
import json
import html
import logging
import asyncio
import subprocess
import threading
from datetime import datetime, time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from src.config import BASE_DIR, ENV_PATH, CONFIG_PATH, load_status
from src import notifications

logger = logging.getLogger("SiGCABot")

def kill_playwright_orphans():
    """
    Busca y termina procesos de Chromium y Node.js huérfanos iniciados por Playwright
    para evitar fugas de memoria o procesos colgados.
    No afecta al navegador Chrome principal del usuario.
    """
    logger.info("Limpiando procesos de Chromium y Node.js de Playwright huérfanos...")
    powershell_cmd = (
        "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { "
        "($_.Name -eq 'chrome.exe' -or $_.Name -eq 'node.exe') -and "
        "($_.ExecutablePath -like '*ms-playwright*' -or $_.ExecutablePath -like '*playwright*') } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", powershell_cmd],
            capture_output=True, text=True, timeout=10
        )
        logger.info("Limpieza de procesos huérfanos completada.")
    except Exception as e:
        logger.warning(f"No se pudo completar la limpieza de procesos huérfanos: {e}")


class LunchBot:
    """Motor principal de automatización del almuerzo en SiGCA."""

    def __init__(self, config_path=None):
        self.config_path = config_path or CONFIG_PATH
        self.load_config()
        self.load_credentials()

    # ------------------------------------------------------------------
    # Configuración y credenciales
    # ------------------------------------------------------------------

    def load_config(self):
        """Carga parámetros operativos desde config.json."""
        logger.debug(f"Cargando configuración desde {self.config_path}")
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            logger.warning("No se encontró config.json, usando valores por defecto.")
            self.config = {
                "start_hour": 15,
                "start_minute": 30,
                "end_hour": 9,
                "end_minute": 59,
                "timeout_ms": 30000,
                "headless": True,
                "retries": 3,
                "retry_delay_sec": 300
            }

    def load_credentials(self):
        """Recarga las variables de entorno desde .env y extrae credenciales."""
        from src.config import load_env_dict
        env = load_env_dict()
        self.username = env.get("SIGCA_USER")
        passwords_raw = env.get("SIGCA_PASSWORDS")
        self.url = env.get("SIGCA_URL", "https://sigca.ex-cle.com/")
        self.telegram_token = env.get("TELEGRAM_TOKEN")
        self.telegram_chat_id = env.get("TELEGRAM_CHAT_ID")

        if not self.username:
            raise ValueError("Falta la variable de entorno SIGCA_USER")
        if not passwords_raw:
            raise ValueError("Falta la variable de entorno SIGCA_PASSWORDS")

        self.passwords = [p.strip() for p in passwords_raw.split(",") if p.strip()]
        if not self.passwords:
            raise ValueError("La lista de contraseñas de SIGCA_PASSWORDS está vacía")

    # ------------------------------------------------------------------
    # Wrappers de notificación (delegan al módulo notifications)
    # ------------------------------------------------------------------

    def _notify_toast(self, title, message):
        threading.Thread(
            target=notifications.send_windows_toast,
            args=(title, message),
            daemon=True
        ).start()

    def _notify_telegram(self, message):
        threading.Thread(
            target=notifications.send_telegram_message,
            args=(self.telegram_token, self.telegram_chat_id, message),
            daemon=True
        ).start()

    def _notify_telegram_photo(self, photo_path, caption=None):
        threading.Thread(
            target=notifications.send_telegram_photo,
            args=(self.telegram_token, self.telegram_chat_id, photo_path, caption),
            daemon=True
        ).start()

    # ------------------------------------------------------------------
    # Validación horaria
    # ------------------------------------------------------------------

    def is_time_valid(self, current_time=None):
        """Verifica si la hora actual está dentro del rango permitido de ejecución."""
        if current_time is None:
            current_time = datetime.now().time()

        start_t = time(
            self.config.get("start_hour", 15),
            self.config.get("start_minute", 30)
        )
        end_t = time(
            self.config.get("end_hour", 10),
            self.config.get("end_minute", 0)
        )

        if start_t <= end_t:
            return start_t <= current_time < end_t
        else:
            # Ventana que cruza la medianoche (ej. 3:30 PM a 9:59 AM)
            return current_time >= start_t or current_time < end_t

    # ------------------------------------------------------------------
    # Captura de evidencias (screenshots)
    # ------------------------------------------------------------------

    def capture_evidence(self, page, name):
        """Toma una captura de pantalla completa y la guarda en evidence/."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}_{name}.png"
        filepath = os.path.join(BASE_DIR, "evidence", filename)
        try:
            page.screenshot(path=filepath, full_page=True)
            logger.info(f"Captura de pantalla guardada: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"No se pudo guardar la captura de pantalla: {e}")
            return None

    # ------------------------------------------------------------------
    # Llenado inteligente de campos de formulario
    # ------------------------------------------------------------------

    def fill_form_field(self, page, label_text, field_type, value):
        """
        Rellena un campo de formulario buscando el contenedor por texto de etiqueta.

        Args:
            page: Instancia de la página de Playwright.
            label_text: Texto de la etiqueta/pregunta del campo.
            field_type: Tipo de campo ('select', 'radio', 'text').
            value: Valor a establecer (string, int, o 'last' para el último).
        """
        try:
            logger.info(f"Intentando rellenar campo '{label_text}' de tipo '{field_type}' con valor '{value}'...")

            # Buscar el contenedor que tiene el texto de la etiqueta
            container = None
            container_selectors = [
                "div.form-group", "div.question", "div.ng-star-inserted",
                "div", "fieldset"
            ]

            for selector in container_selectors:
                locs = page.locator(f"{selector}:has-text('{label_text}')")
                count = locs.count()
                for i in range(count):
                    candidate = locs.nth(i)
                    if candidate.locator("select, input, textarea, [role='combobox'], [role='radiogroup']").count() > 0:
                        container = candidate

            if not container:
                logger.warning(f"No se encontró contenedor específico para '{label_text}'. Buscando de forma global.")
                container = page

            if field_type == "select":
                select_loc = container.locator("select, [role='combobox']").first
                if select_loc.count() > 0 and select_loc.is_visible():
                    tag_name = select_loc.evaluate("el => el.tagName.toLowerCase()")
                    if tag_name == "select":
                        if isinstance(value, int):
                            select_loc.select_option(index=value)
                        elif value == "last":
                            options_count = select_loc.locator("option").count()
                            select_loc.select_option(index=options_count - 1)
                        else:
                            select_loc.select_option(label=value)
                    else:
                        # Custom Angular Material/etc. select
                        select_loc.click()
                        page.wait_for_timeout(1000)
                        options_selector = "option, [role='option'], mat-option, div.option"
                        options = page.locator(options_selector)
                        if value == "last":
                            if options.count() > 0:
                                options.last.click()
                        elif isinstance(value, int):
                            if options.count() > value:
                                options.nth(value).click()
                        else:
                            option_item = page.locator(options_selector, has_text=value).first
                            if option_item.count() > 0:
                                option_item.click()
                    logger.info(f"Campo '{label_text}' seleccionado con éxito.")
                    return True

            elif field_type == "radio":
                # 1. Por rol de radio con nombre exacto
                loc = container.get_by_role("radio", name=value, exact=True)
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    logger.info(f"Marcado radio button por rol con nombre exacto: '{value}'")
                    return True

                # 2. Por texto exacto (variaciones Sí/Si)
                alternatives = [value]
                if value == "Si":
                    alternatives.append("Sí")
                elif value == "Sí":
                    alternatives.append("Si")

                for val in alternatives:
                    exact_text_loc = container.get_by_text(val, exact=True)
                    count = exact_text_loc.count()
                    for i in range(count):
                        el = exact_text_loc.nth(i)
                        if el.is_visible():
                            el.click()
                            logger.info(f"Marcado radio button por clic en texto exacto: '{val}'")
                            return True

                # 3. Fallback con selectores estándar
                radio_selectors = [
                    f"input[type='radio'][value='{value}']",
                    f"[role='radio'][aria-label*='{value}' i]",
                    f"[role='radio']:has-text('{value}')",
                    f"label:has-text('{value}')",
                    f"span:has-text('{value}')"
                ]
                for sel in radio_selectors:
                    loc = container.locator(sel)
                    for i in range(loc.count()):
                        el = loc.nth(i)
                        if el.is_visible():
                            el.click()
                            logger.info(f"Campo de opción única '{label_text}' marcado con '{value}' con selector '{sel}'")
                            return True

            elif field_type == "text":
                text_loc = container.locator("input[type='text'], textarea").first
                if text_loc.count() > 0 and text_loc.is_visible():
                    text_loc.fill(value)
                    logger.info(f"Campo de texto '{label_text}' rellenado.")
                    return True

        except Exception as e:
            logger.error(f"Excepción al rellenar el campo '{label_text}': {e}")

        logger.warning(f"No se pudo rellenar el campo '{label_text}'")
        return False

    # ------------------------------------------------------------------
    # Inicio de sesión (SSO Microsoft + Formulario estándar)
    # ------------------------------------------------------------------

    def attempt_login(self, page, password):
        """Intenta iniciar sesión en SiGCA con una contraseña dada."""
        logger.info(f"Intentando iniciar sesión con el usuario: {self.username} y contraseña tentativa...")

        timeout = self.config.get("timeout_ms", 30000)

        try:
            page.goto(self.url, wait_until="networkidle", timeout=timeout)
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Fallo de conexión al cargar la URL {self.url}: {err_msg}")
            
            if "ERR_INTERNET_DISCONNECTED" in err_msg or "ERR_NAME_NOT_RESOLVED" in err_msg:
                reason = "No hay conexión a Internet o el DNS no puede resolver la dirección."
            elif "ERR_CONNECTION_REFUSED" in err_msg or "ERR_CONNECTION_TIMED_OUT" in err_msg:
                reason = "El servidor de SiGCA rechazó la conexión o está fuera de línea."
            elif "Timeout" in err_msg or "timeout" in err_msg.lower():
                reason = f"Tiempo de espera agotado ({timeout/1000:.1f}s) cargando la página principal. Posible conexión lenta o servidor saturado."
            else:
                reason = "Fallo de conexión o red desconocido al acceder a SiGCA."
            
            raise ConnectionError(f"{reason} (Detalle técnico: {err_msg})")

        ms_sso_button = "button:has-text('Continuar con Microsoft'), button:has-text('Microsoft')"
        email_selector = "input[type='email'], input[placeholder*='usuario' i], input[placeholder*='correo' i], input[placeholder*='email' i], input[formcontrolname='email']"
        password_selector = "input[type='password'], input[placeholder*='contraseña' i], input[placeholder*='clave' i], input[formcontrolname='password']"
        submit_selector = "button[type='submit'], button:has-text('Iniciar'), button:has-text('Ingresar'), button:has-text('Login')"


        # Determinar si nos encontramos con SSO de Microsoft
        page.wait_for_timeout(2000)
        is_sso = False
        try:
            if page.locator(ms_sso_button).is_visible(timeout=5000):
                logger.info("Se detectó botón de SSO de Microsoft. Iniciando flujo SSO...")
                is_sso = True
        except Exception:
            pass

        if is_sso:
            self.capture_evidence(page, "before_sso_click")
            page.click(ms_sso_button)

            ms_email_selector = "input[type='email'], input[name='loginfmt'], #i0116"
            page.wait_for_selector(ms_email_selector, timeout=timeout)
            page.fill(ms_email_selector, self.username)
            self.capture_evidence(page, "ms_sso_email_filled")

            ms_next_selector = "#idSIButton9, input[type='submit']"
            page.click(ms_next_selector)

            ms_password_selector = "input[type='password'], input[name='passwd'], #i0118"
            page.wait_for_selector(ms_password_selector, timeout=timeout)
            page.wait_for_timeout(1000)

            page.fill(ms_password_selector, password)
            self.capture_evidence(page, "ms_sso_password_filled")

            ms_submit_selector = "#idSIButton9, input[type='submit']"
            page.click(ms_submit_selector)
            page.wait_for_timeout(2000)

            if page.locator("#passwordError").is_visible() or page.locator("#usernameError").is_visible():
                error_txt = page.locator("#passwordError").text_content() or page.locator("#usernameError").text_content() or "Error de credenciales"
                logger.warning(f"Error detectado en formulario de Microsoft SSO: {error_txt.strip()}")
                self.capture_evidence(page, "ms_sso_error_detected")
                return False

            ms_stay_signed_in_selector = "#idSIButton9, input[type='submit']"
            try:
                if page.locator(ms_stay_signed_in_selector).is_visible(timeout=5000):
                    logger.info("Confirmando diálogo '¿Mantener la sesión iniciada?' de Microsoft...")
                    self.capture_evidence(page, "ms_sso_stay_signed_in_prompt")
                    page.click(ms_stay_signed_in_selector)
            except Exception:
                pass
        else:
            logger.info("Procediendo con inicio de sesión estándar de formulario...")
            page.wait_for_selector(email_selector, timeout=timeout)
            page.fill(email_selector, self.username)
            page.fill(password_selector, password)
            self.capture_evidence(page, "before_login_submit")
            page.click(submit_selector)

        logger.info("Esperando redirección post-login...")
        try:
            page.wait_for_function(
                "() => !window.location.href.includes('microsoftonline') && !window.location.href.includes('login')",
                timeout=15000
            )
        except Exception:
            pass

        current_url = page.url
        logger.info(f"URL actual después del envío de login: {current_url}")

        if "login" in current_url.lower() or "microsoft" in current_url.lower():
            logger.warning("Fallo en el login (se mantiene en la página de autenticación)")
            return False

        logger.info("¡Inicio de sesión exitoso!")
        self.capture_evidence(page, "login_success")
        return True

    # ------------------------------------------------------------------
    # Flujo principal de automatización del almuerzo
    # ------------------------------------------------------------------

    def run_automation(self, dry_run=False, is_manual=False):
        """
        Ejecuta el flujo completo de solicitud de almuerzo con hasta 3 intentos incrementales.

        Args:
            dry_run: Si es True, no confirma el pedido final.
            is_manual: Si es True, ignora la validación de cancelación diaria.

        Returns:
            Tupla (exit_code, message, evidence_path)
            - exit_code 0: éxito
            - exit_code 1: error de login
            - exit_code 2: formulario cerrado / no encontrado
            - exit_code 3: error crítico
        """
        sim_str = " (SIMULACIÓN)" if dry_run else ""
        
        # 1. Validaciones tempranas y estáticas (se ejecutan antes del navegador)
        try:
            if not is_manual:
                status_data = load_status()
                if status_data.get("is_cancelled_today", False):
                    msg = "El bot está inactivo hoy porque el almuerzo fue cancelado."
                    logger.warning(msg)
                    return 0, msg, None

                # Validar días deshabilitados (libres/remotos)
                disabled_days = self.config.get("disabled_days", [])
                if disabled_days:
                    dias_semana = {
                        0: "Lunes",
                        1: "Martes",
                        2: "Miércoles",
                        3: "Jueves",
                        4: "Viernes",
                        5: "Sábado",
                        6: "Domingo"
                    }
                    today_name = dias_semana.get(datetime.now().weekday())
                    if today_name in disabled_days:
                        msg = f"Hoy es {today_name}, marcado como día libre/remoto en la configuración. Ejecución cancelada automáticamente."
                        logger.info(msg)
                        return 0, msg, None

            if not dry_run and not self.is_time_valid():
                msg = "Fuera de horario de ejecución (3:30 PM - 9:59 AM)."
                logger.warning(msg)
                return 0, msg, None
                
        except Exception as e:
            msg = f"Error en validaciones iniciales de automatización: {e}"
            logger.error(msg, exc_info=True)
            return 3, msg, None

        # 2. Configurar bucle de reintentos incrementales (hasta 3 intentos)
        max_attempts = 3
        base_timeout_ms = 60000  # 1 minuto base para solicitud
        
        last_exit_code = 3
        last_msg = ""
        last_evidence = None

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Iniciando intento de solicitud {attempt}/{max_attempts}...")
            factor = 1.0 + (attempt - 1) * 0.5
            current_timeout_ms = int(base_timeout_ms * factor)
            
            try:
                kill_playwright_orphans()

                # Asegurar bucle de eventos asyncio en este hilo
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if attempt == 1:
                    self._notify_toast(f"Iniciando Bot{sim_str}", "Comenzando automatización del almuerzo en SiGCA...")
                    self._notify_telegram(f"🤖 <b>SiGCA Bot{sim_str}</b>:\nComenzando automatización del almuerzo...")

                with sync_playwright() as p:
                    headless = self.config.get("headless", True)
                    logger.info(f"Intento {attempt}: Iniciando navegador Chromium (headless={headless}, timeout={current_timeout_ms}ms)...")
                    if attempt == 1:
                        self._notify_telegram("🌐 <b>Navegador</b>:\nIniciando navegador Chromium en segundo plano...")

                    browser = p.chromium.launch(headless=headless)
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    context.set_default_timeout(current_timeout_ms)
                    page = context.new_page()
                    page.set_default_timeout(current_timeout_ms)

                    # Intentar login
                    if attempt == 1:
                        self._notify_telegram("🔑 <b>Autenticación</b>:\nNavegador iniciado. Intentando iniciar sesión...")
                    
                    login_success = False
                    for pwd in self.passwords:
                        try:
                            if self.attempt_login(page, pwd):
                                login_success = True
                                break
                        except ConnectionError as ce:
                            logger.error(f"Intento {attempt}: Error de conexión detectado. Abortando contraseñas: {ce}")
                            last_msg = f"Error de conexión o red al acceder a SiGCA: {ce}"
                            last_evidence = None
                            try:
                                last_evidence = self.capture_evidence(page, f"connection_failed_att{attempt}")
                            except Exception:
                                pass
                            try:
                                browser.close()
                            except Exception:
                                pass
                            raise ce
                        except Exception as e:
                            logger.error(f"Intento {attempt}: Excepción durante login: {e}")
                            try:
                                self.capture_evidence(page, f"login_error_exception_att{attempt}")
                            except Exception:
                                pass

                    if not login_success:
                        last_msg = "No se pudo iniciar sesión con ninguna de las contraseñas provistas."
                        logger.error(f"Intento {attempt}: {last_msg}")
                        last_evidence = self.capture_evidence(page, f"login_failed_att{attempt}")
                        browser.close()
                        # Si es un error de credenciales incorrectas permanente, no reintentamos
                        self._notify_toast("Error de Login - SiGCA", "No se pudo iniciar sesión. Revisa tus credenciales.")
                        self._notify_telegram(f"❌ <b>Error de Inicio de Sesión SiGCA</b>:\n{html.escape(last_msg)}")
                        if last_evidence:
                            self._notify_telegram_photo(last_evidence, "Error de Inicio de Sesión")
                        return 1, last_msg, last_evidence

                    try:
                        # --- Navegación a la sección de almuerzo ---
                        logger.info(f"Intento {attempt}: Navegando a la sección de almuerzo/pedidos...")
                        if attempt == 1:
                            self._notify_telegram("🍱 <b>Sección de Almuerzos</b>:\nBuscando el formulario de solicitud...")

                        lunch_keywords = ["Almuerzo", "Solicitud de Almuerzo", "Pedir Almuerzo", "Menú", "Servicios"]
                        lunch_navigated = False
                        page.wait_for_timeout(int(3000 * factor))

                        for keyword in lunch_keywords:
                            locator = page.get_by_text(keyword, exact=False)
                            if locator.count() > 0:
                                logger.info(f"Se encontró enlace/botón de navegación con palabra clave '{keyword}'. Haciendo clic...")
                                locator.first.click()
                                page.wait_for_timeout(int(2000 * factor))
                                lunch_navigated = True
                                break

                        if not lunch_navigated:
                            logger.warning("No se encontró link directo. Buscando en elementos del menú...")
                            self.capture_evidence(page, f"dashboard_search_att{attempt}")
                            nav_links = page.locator("a, button, li")
                            for i in range(nav_links.count()):
                                txt = nav_links.nth(i).text_content() or ""
                                if any(kw.lower() in txt.lower() for kw in lunch_keywords):
                                    logger.info(f"Haciendo clic en el menú '{txt.strip()}'...")
                                    nav_links.nth(i).click()
                                    page.wait_for_timeout(int(2000 * factor))
                                    lunch_navigated = True
                                    break

                        self.capture_evidence(page, f"lunch_section_att{attempt}")

                        # Verificar si ya fue solicitado
                        page_text = page.content().lower()
                        already_ordered_keywords = [
                            "ya solicitado", "solicitado con éxito", "almuerzo pedido",
                            "pedido registrado", "ya has solicitado", "solicitud registrada",
                            "has realizado tu solicitud", "tu pedido ha sido procesado exitosamente",
                            "¡solicitud registrada!"
                        ]

                        already_ordered = False
                        for kw in already_ordered_keywords:
                            if kw in page_text:
                                logger.info(f"Se detectó almuerzo ya solicitado previamente (coincidencia con '{kw}').")
                                already_ordered = True
                                break

                        if already_ordered:
                            last_msg = "El almuerzo ya ha sido solicitado para hoy/mañana. No se requiere acción adicional."
                            logger.info(last_msg)
                            last_evidence = self.capture_evidence(page, f"lunch_already_ordered_att{attempt}")
                            browser.close()
                            self._notify_toast("Almuerzo Ya Solicitado", "El almuerzo ya fue solicitado previamente.")
                            self._notify_telegram(f"ℹ️ <b>SiGCA Bot</b>:\n{html.escape(last_msg)}")
                            return 0, last_msg, last_evidence

                        # Verificar si el formulario está cerrado
                        closed_keywords = ["formulario cerrado", "el horario de solicitud de almuerzo ha finalizado"]
                        is_closed = False
                        for kw in closed_keywords:
                            if kw in page_text:
                                logger.warning(f"Se detectó que el formulario está cerrado (coincidencia con '{kw}').")
                                is_closed = True
                                break

                        if is_closed:
                            last_msg = "El formulario de solicitud de almuerzo está cerrado y no se pudo realizar el pedido."
                            logger.error(last_msg)
                            last_evidence = self.capture_evidence(page, f"lunch_form_closed_att{attempt}")
                            browser.close()
                            self._notify_toast("Formulario Cerrado - SiGCA", "El horario de solicitud ha finalizado.")
                            self._notify_telegram(f"⚠️ <b>Formulario Cerrado en SiGCA</b>:\n{html.escape(last_msg)}")
                            if last_evidence:
                                self._notify_telegram_photo(last_evidence, "Formulario Cerrado")
                            return 2, last_msg, last_evidence

                        # --- Selección de Menú ---
                        prefer_menu = self.config.get("prefer_menu", "saludable").lower()
                        logger.info(f"Preferencia de menú configurada: {prefer_menu}")
                        if attempt == 1:
                            self._notify_telegram(f"📝 <b>Selección de Menú</b>:\nIntentando seleccionar el menú favorito: <code>{html.escape(prefer_menu.capitalize())}</code>...")

                        menu_selected = False
                        try:
                            target_label = "Saludable" if prefer_menu == "saludable" else "Estándar"
                            alternative_label = "Estándar" if prefer_menu == "saludable" else "Saludable"

                            menu_selectors = [
                                f"text={target_label}",
                                f"input[value*='{target_label.lower()}']",
                                f"label:has-text('{target_label}')",
                                f"span:has-text('{target_label}')"
                            ]

                            for sel in menu_selectors:
                                loc = page.locator(sel)
                                if loc.count() > 0 and loc.first.is_visible():
                                    logger.info(f"Seleccionando menú preferido clicking en: '{sel}'")
                                    loc.first.click()
                                    page.wait_for_timeout(int(1000 * factor))
                                    menu_selected = True
                                    break

                            if not menu_selected:
                                logger.warning(f"No se pudo seleccionar el menú preferido '{target_label}'. Intentando alternativo '{alternative_label}'...")
                                alt_selectors = [
                                    f"text={alternative_label}",
                                    f"input[value*='{alternative_label.lower()}']",
                                    f"label:has-text('{alternative_label}')",
                                    f"span:has-text('{alternative_label}')"
                                ]
                                for sel in alt_selectors:
                                    loc = page.locator(sel)
                                    if loc.count() > 0 and loc.first.is_visible():
                                        logger.info(f"Seleccionando menú alternativo clicking en: '{sel}'")
                                        loc.first.click()
                                        page.wait_for_timeout(int(1000 * factor))
                                        menu_selected = True
                                        break
                        except Exception as e:
                            logger.error(f"Error intentando seleccionar la opción de menú: {e}")

                        # --- Rellenar campos condicionales si existen ---
                        logger.info("Verificando existencia de campos del formulario adicional...")

                        q_config = self.config.get("questionnaire", {})
                        ubicacion_val = q_config.get("ubicacion", "Sede ExCle")
                        estrellas_val = q_config.get("estrellas", "3")
                        bien_cocidos_val = q_config.get("bien_cocidos", "last")
                        porcion_acorde_val = q_config.get("porcion_acorde", "last")
                        condimentacion_val = q_config.get("condimentacion", 1)
                        asistir_tarde_val = q_config.get("asistir_tarde", "Sí")
                        comentario_val = q_config.get("comentario", "Favor quitar el jugo de melon y las porciones no tienen suficiente proteina, quedando uno con hambre")

                        if page.get_by_text("Ubicación", exact=False).count() > 0:
                            self.fill_form_field(page, "Ubicación", "select", ubicacion_val)

                        if page.get_by_text("De 1 a 5 estrellas", exact=False).count() > 0:
                            self.fill_form_field(page, "De 1 a 5 estrellas", "radio", estrellas_val)

                        if page.get_by_text("bien cocidos", exact=False).count() > 0:
                            self.fill_form_field(page, "bien cocidos", "select", bien_cocidos_val)

                        if page.get_by_text("porción estaba acorde", exact=False).count() > 0:
                            self.fill_form_field(page, "porción estaba acorde", "select", porcion_acorde_val)

                        if page.get_by_text("condimentación de la comida", exact=False).count() > 0:
                            try:
                                cond_val = int(condimentacion_val)
                            except ValueError:
                                cond_val = condimentacion_val
                            self.fill_form_field(page, "condimentación de la comida", "select", cond_val)

                        if page.get_by_text("asistir después de la 01:30", exact=False).count() > 0:
                            self.fill_form_field(page, "asistir después de la 01:30", "radio", asistir_tarde_val)

                        if page.get_by_text("comentario acerca del plato", exact=False).count() > 0:
                            self.fill_form_field(page, "comentario acerca del plato", "text", comentario_val)

                        last_evidence = self.capture_evidence(page, f"form_filled_att{attempt}")

                        # --- Buscar botón de envío ---
                        submit_buttons = ["Solicitar", "Pedir Almuerzo", "Guardar", "Confirmar", "Enviar", "Aceptar"]
                        button_found = None

                        for btn_text in submit_buttons:
                            btn_locator = page.get_by_role("button", name=btn_text, exact=False)
                            if btn_locator.count() > 0 and btn_locator.first.is_visible():
                                button_found = btn_locator.first
                                logger.info(f"Se encontró botón de acción: '{btn_text}'")
                                break
                            text_locator = page.get_by_text(btn_text, exact=True)
                            if text_locator.count() > 0 and text_locator.first.is_visible():
                                button_found = text_locator.first
                                logger.info(f"Se encontró elemento clicable con texto: '{btn_text}'")
                                break

                        if not button_found:
                            last_msg = "No se pudo identificar el botón o formulario de pedido de almuerzo en la página."
                            logger.error(f"Intento {attempt}: {last_msg}")
                            last_evidence = self.capture_evidence(page, f"lunch_form_not_found_att{attempt}")
                            browser.close()
                            raise RuntimeError(last_msg)

                        if dry_run:
                            last_msg = "[DRY RUN] Se encontró el botón de pedido pero NO se hizo clic para no generar un pedido real."
                            logger.info(last_msg)
                            last_evidence = self.capture_evidence(page, f"dry_run_success_att{attempt}")
                            browser.close()
                            self._notify_toast("Prueba de Pedido (Dry-Run)", "Simulación completada con éxito.")
                            self._notify_telegram(f"🤖 <b>Prueba Dry-Run Exitosa</b>:\n{html.escape(last_msg)}")
                            if last_evidence:
                                self._notify_telegram_photo(last_evidence, "Dry Run Completado")
                            return 0, last_msg, last_evidence
                        else:
                            logger.info("Haciendo clic en el botón de solicitud...")
                            button_found.click()

                            status_text = "El mensaje de éxito apareció en pantalla. Solicitud confirmada."
                            try:
                                success_message = page.get_by_text("Solicitud Registrada", exact=False).or_(
                                    page.get_by_text("procesado exitosamente", exact=False)
                                ).first
                                success_message.wait_for(state="visible", timeout=int(10000 * factor))
                                logger.info(status_text)
                            except PlaywrightTimeoutError:
                                status_text = "No se detectó el mensaje de éxito después de enviar. Puede que esté lento o haya fallado."
                                logger.warning(status_text)

                            last_evidence = self.capture_evidence(page, f"post_order_click_att{attempt}")
                            last_msg = f"Solicitud exitosa: {status_text}"
                            logger.info("Flujo de solicitud completado. Registrando éxito.")
                            browser.close()

                            self._notify_toast("Almuerzo Solicitado", "¡La solicitud de almuerzo ha sido registrada exitosamente!")
                            self._notify_telegram(f"✅ <b>Almuerzo Solicitado Exitosamente</b>:\n{html.escape(status_text)}")
                            if last_evidence:
                                self._notify_telegram_photo(last_evidence, "Confirmación de Pedido")
                            return 0, last_msg, last_evidence

                    except Exception as inner_e:
                        logger.error(f"Intento {attempt}: Error en flujo de automatización: {inner_e}")
                        try:
                            last_evidence = self.capture_evidence(page, f"error_runtime_att{attempt}")
                        except Exception:
                            pass
                        last_msg = str(inner_e)
                        last_exit_code = 3
                        try:
                            browser.close()
                        except Exception:
                            pass

            except Exception as e:
                logger.error(f"Intento {attempt}: Error crítico en el intento de solicitud: {e}")
                last_msg = str(e)
                last_exit_code = 3
            finally:
                kill_playwright_orphans()

            # Esperar 5s antes del siguiente reintento (si aplica)
            if attempt < max_attempts:
                import time as time_mod
                wait_time = 5
                logger.info(f"Esperando {wait_time}s antes de reintentar...")
                time_mod.sleep(wait_time)

        # Fallo Definitivo tras 3 intentos
        logger.error(f"Todos los {max_attempts} intentos de solicitud fallaron. Último error: {last_msg}")
        
        # Filtros de mensaje amigables
        if "No se pudo identificar el botón" in last_msg:
            self._notify_toast("Error de Pedido", "No se encontró el botón para solicitar el almuerzo.")
            self._notify_telegram(f"⚠️ <b>Error en SiGCA</b>:\n<pre>{html.escape(last_msg)}</pre>")
            if last_evidence:
                self._notify_telegram_photo(last_evidence, "Formulario No Identificado")
            return 2, last_msg, last_evidence

        self._notify_toast("Error en Automatización", "Ocurrió un error inesperado al procesar la solicitud tras 3 intentos.")
        self._notify_telegram(f"❌ <b>Fallo en Automatización de Almuerzo (3 intentos)</b>:\n<pre>{html.escape(last_msg)}</pre>")
        if last_evidence:
            self._notify_telegram_photo(last_evidence, "Captura de Error de Solicitud (Último Intento)")
            
        return last_exit_code, last_msg, last_evidence

    # ------------------------------------------------------------------
    # Cancelación de pedido de almuerzo
    # ------------------------------------------------------------------

    def cancel_lunch_order(self):
        """
        Ejecuta el flujo de cancelación de la solicitud de almuerzo con hasta 3 intentos incrementales.

        Returns:
            Tupla (exit_code, message, evidence_path)
        """
        max_attempts = 3
        base_timeout_ms = self.config.get("timeout_ms", 30000)
        
        self._notify_toast("Cancelando Almuerzo", "Iniciando proceso de cancelación en SiGCA...")
        self._notify_telegram("🤖 <b>SiGCA Bot</b>:\nIniciando cancelación de solicitud de almuerzo...")

        last_exit_code = 3
        last_msg = ""
        last_evidence = None

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Iniciando intento de cancelación {attempt}/{max_attempts}...")
            factor = 1.0 + (attempt - 1) * 0.5
            current_timeout_ms = int(base_timeout_ms * factor)
            
            try:
                kill_playwright_orphans()

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                with sync_playwright() as p:
                    headless = self.config.get("headless", True)
                    logger.info(f"Intento {attempt}: Iniciando navegador Chromium (headless={headless}, timeout={current_timeout_ms}ms)...")
                    browser = p.chromium.launch(headless=headless)
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    context.set_default_timeout(current_timeout_ms)
                    page = context.new_page()
                    page.set_default_timeout(current_timeout_ms)

                    try:
                        # Intentar login
                        login_success = False
                        for pwd in self.passwords:
                            try:
                                if self.attempt_login(page, pwd):
                                    login_success = True
                                    break
                            except ConnectionError as ce:
                                logger.error(f"Intento {attempt}: Error de conexión detectado. Abortando contraseñas: {ce}")
                                last_msg = f"Error de conexión o red al intentar cancelar: {ce}"
                                last_evidence = None
                                try:
                                    last_evidence = self.capture_evidence(page, f"cancel_connection_failed_att{attempt}")
                                except Exception:
                                    pass
                                try:
                                    browser.close()
                                except Exception:
                                    pass
                                raise ce
                            except Exception as e:
                                logger.error(f"Intento {attempt}: Excepción durante login: {e}")

                        if not login_success:
                            last_msg = "No se pudo iniciar sesión para realizar la cancelación."
                            logger.error(f"Intento {attempt}: {last_msg}")
                            last_evidence = self.capture_evidence(page, f"cancel_login_failed_att{attempt}")
                            browser.close()
                            raise RuntimeError(last_msg)

                        # Navegación a almuerzos
                        logger.info(f"Intento {attempt}: Navegando a la sección de almuerzos...")
                        lunch_keywords = ["Almuerzo", "Solicitud de Almuerzo", "Pedir Almuerzo", "Menú", "Servicios"]
                        lunch_navigated = False
                        page.wait_for_timeout(int(3000 * factor))

                        for keyword in lunch_keywords:
                            locator = page.get_by_text(keyword, exact=False)
                            if locator.count() > 0:
                                locator.first.click()
                                page.wait_for_timeout(int(2000 * factor))
                                lunch_navigated = True
                                break

                        if not lunch_navigated:
                            nav_links = page.locator("a, button, li")
                            for i in range(nav_links.count()):
                                txt = nav_links.nth(i).text_content() or ""
                                if any(kw.lower() in txt.lower() for kw in lunch_keywords):
                                    nav_links.nth(i).click()
                                    page.wait_for_timeout(int(2000 * factor))
                                    lunch_navigated = True
                                    break

                        self.capture_evidence(page, f"cancel_section_att{attempt}")

                        # Buscar botón "Cancelar solicitud"
                        cancel_button = page.locator("button:has-text('Cancelar solicitud')").first

                        if cancel_button.count() == 0 or not cancel_button.is_visible():
                            last_msg = "No se encontró ningún botón activo para cancelar la solicitud en la página."
                            logger.warning(f"Intento {attempt}: {last_msg}")
                            last_evidence = self.capture_evidence(page, f"cancel_button_not_found_att{attempt}")
                            browser.close()
                            raise RuntimeError(last_msg)

                        if cancel_button.is_disabled():
                            last_msg = "El botón de cancelar solicitud está deshabilitado."
                            logger.warning(f"Intento {attempt}: {last_msg}")
                            last_evidence = self.capture_evidence(page, f"cancel_button_disabled_att{attempt}")
                            browser.close()
                            raise RuntimeError(last_msg)

                        # Hacer clic en cancelar
                        logger.info(f"Intento {attempt}: Haciendo clic en el botón 'Cancelar solicitud'...")
                        cancel_button.click()

                        # Esperar modal de confirmación
                        logger.info(f"Intento {attempt}: Esperando el modal de confirmación...")
                        confirm_button = page.get_by_role("button", name="Sí, cancelar")
                        confirm_button.wait_for(state="visible", timeout=int(10000 * factor))
                        confirm_button.click()

                        page.wait_for_timeout(int(3000 * factor))

                        last_evidence = self.capture_evidence(page, f"cancel_success_att{attempt}")
                        last_msg = "La solicitud de almuerzo ha sido cancelada con éxito."
                        logger.info(f"Intento {attempt}: {last_msg}")
                        browser.close()

                        # Éxito: Notificar de forma definitiva
                        self._notify_toast("Cancelación Exitosa", "Tu solicitud de almuerzo ha sido cancelada correctamente.")
                        self._notify_telegram(f"🚫 <b>Cancelación Exitosa</b>:\n{last_msg}")
                        if last_evidence:
                            self._notify_telegram_photo(last_evidence, "Confirmación de Cancelación")
                        return 0, last_msg, last_evidence

                    except Exception as inner_e:
                        logger.error(f"Intento {attempt}: Error en flujo de cancelación interno: {inner_e}")
                        try:
                            last_evidence = self.capture_evidence(page, f"cancel_error_runtime_att{attempt}")
                        except Exception:
                            pass
                        last_msg = str(inner_e)
                        last_exit_code = 3
                        try:
                            browser.close()
                        except Exception:
                            pass

            except Exception as e:
                logger.error(f"Intento {attempt}: Error crítico en el intento de cancelación: {e}")
                last_msg = str(e)
                last_exit_code = 3
            finally:
                kill_playwright_orphans()

            # Esperar 5s antes del siguiente reintento (si aplica)
            if attempt < max_attempts:
                import time as time_mod
                wait_time = 5
                logger.info(f"Esperando {wait_time}s antes de reintentar...")
                time_mod.sleep(wait_time)

        # Fallo Definitivo
        logger.error(f"Todos los {max_attempts} intentos de cancelación fallaron. Último error: {last_msg}")
        
        # Filtros de mensaje amigables
        if "No se encontró ningún botón activo" in last_msg:
            self._notify_toast("Cancelación no Disponible", "No hay una solicitud activa que cancelar.")
            self._notify_telegram(f"ℹ️ <b>SiGCA Bot</b>:\n{last_msg}")
            if last_evidence:
                self._notify_telegram_photo(last_evidence, "Pantalla de Cancelación no Disponible")
            return 2, last_msg, last_evidence
        
        if "deshabilitado" in last_msg:
            self._notify_toast("Cancelación no Disponible", "El botón de cancelación está bloqueado.")
            self._notify_telegram(f"ℹ️ <b>SiGCA Bot</b>:\n{last_msg}")
            if last_evidence:
                self._notify_telegram_photo(last_evidence, "Botón de Cancelación Deshabilitado")
            return 2, last_msg, last_evidence

        self._notify_toast("Error al Cancelar", "Ocurrió un error inesperado al cancelar tras 3 intentos.")
        self._notify_telegram(f"❌ <b>Fallo al Cancelar Almuerzo (3 intentos)</b>:\n<pre>{html.escape(last_msg)}</pre>")
        if last_evidence:
            self._notify_telegram_photo(last_evidence, "Captura de Error de Cancelación (Último Intento)")
            
        return last_exit_code, last_msg, last_evidence
