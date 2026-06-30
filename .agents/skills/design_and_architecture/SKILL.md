---
name: design_and_architecture
description: Guidelines for managing the layered architecture, configuration files, and Tkinter GUI styling of the SiGCABot application.
---

# Skill: Design & Architecture (SiGCABot)

Esta habilidad proporciona las directrices y estándares para extender, modificar o mantener la arquitectura y la interfaz gráfica del robot.

## 📐 Capas del Proyecto y Arquitectura Modular

El proyecto está diseñado bajo una arquitectura limpia y modular de tres capas principales:

1. **Capa de Presentación / CLI (Entrada):**
   - [app_gui.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/app_gui.py) inicializa Tkinter y maneja la ventana, diálogos premium y bandeja de sistema (`pystray`).
   - También parsea argumentos de consola para actuar como un comando directo para Windows Task Scheduler sin cargar la GUI.
   
2. **Capa de Negocio / Automatización:**
   - [src/bot_engine.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/bot_engine.py) encapsula el motor de Playwright. Realiza el flujo en sí: navegación, inicio de sesión Microsoft SSO con contraseñas alternativas y selección inteligente de campos de formulario.
   - [src/scheduler.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/scheduler.py) planifica las revisiones horarias e interactúa con el Programador de Tareas.
   - [src/telegram_poller.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/telegram_poller.py) y [src/health_server.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/health_server.py) proveen interfaces externas para monitoreo web y chat de Telegram.

3. **Capa de Infraestructura / Configuración:**
   - [src/config.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/config.py) y [src/logger.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/logger.py) gestionan la persistencia y la redirección de logs.

---

## 🎨 Guía de Estilo Visual (Dark Mode Premium)

Toda modificación en los widgets de Tkinter debe respetar la paleta de colores premium inspirada en el tema *Catppuccin*:

```python
BG_MAIN = "#1e1e2e"       # Fondo principal de ventanas
BG_CARD = "#252538"       # Fondo de marcos/paneles internos y diálogos
BG_INPUT = "#313244"      # Fondo de cajas de entrada de texto
FG_TEXT = "#cdd6f4"       # Color del texto general
FG_MUTED = "#a6adc8"      # Color del texto secundario o etiquetas de estado
ACCENT = "#b4befe"        # Color de resalte/bordes/botones activos
ACCENT_GREEN = "#a6e3a1"  # Éxito (pedido exitoso, bot activo)
ACCENT_RED = "#f38ba8"    # Error (fallo, bot inactivo, cancelar)
ACCENT_YELLOW = "#f9e2af" # Advertencias
ACCENT_BLUE = "#89b4fa"   # Información / Enlaces
```

### Reglas para Componentes de Interfaz
- **Estilo de Botón Premium:** Los botones deben usar un borde plano, color de fondo oscuro (`BG_INPUT` o `BG_CARD`) y cambiar dinámicamente con `activebackground` y enlazando los eventos `<Enter>` y `<Leave>` para crear efectos hover elegantes.
- **Cuadros de Diálogo Personalizados:** No usar `messagebox` estándar de Tkinter. En su lugar, instanciar `PremiumMessageBox` (definido en [app_gui.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/app_gui.py)) para mantener la coherencia estética en modo oscuro.

---

## 💾 Persistencia de Archivos y Configuración

Los archivos de persistencia residen en el directorio de ejecución (`BASE_DIR`):

1. **[.env](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/.env):** Almacena credenciales críticas. Las claves obligatorias son `SIGCA_USER`, `SIGCA_PASSWORDS` (delimitadas por comas), `SIGCA_URL`, `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`.
2. **[config.json](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/config.json):** Opciones de comportamiento como horario de inicio/fin, modo headless, reintentos y menú preferido.
3. **[status.json](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/status.json):** Estado del servicio, estatus del último intento y marcas temporales para evitar ejecuciones repetidas el mismo día.

*Cualquier actualización a la configuración a través de la GUI debe ser guardada invocando las funciones thread-safe en [src/config.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/src/config.py).*
