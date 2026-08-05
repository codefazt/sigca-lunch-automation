---
name: notification_designs
description: Guidelines and design system rules for creating styled notification popups, dialog boxes, and toasts within the SiGCABot application.
---

# Skill: Notification & Popup Designs (SiGCABot)

Esta habilidad documenta las directrices y estándares para el diseño de ventanas emergentes (popups), cuadros de diálogo modal (confirmaciones, alertas y errores) y notificaciones de escritorio en **SiGCABot**, garantizando que nunca se use el estilo estándar gris de Windows y se mantenga la estética *Hextech Client* premium.

## 🎨 Principios de Diseño para Notificaciones y Modales

1. **Evitar Ventanas Estándar del SO:** 
   - No utilizar `messagebox.showinfo`, `messagebox.showerror` o diálogos nativos del sistema que rompan la estética de modo oscuro.
   - En su lugar, instanciar componentes visuales basados en `tk.Toplevel` que usen colores de la paleta del proyecto.
   
2. **Coherencia Cromática:**
   - **Fondo:** Siempre usar `BG_CARD` (`#091428`) para el cuerpo interno del popup y `BG_MAIN` (`#010a13`) para las divisiones secundarias.
   - **Borde de Alerta:** El marco exterior debe tener un borde resaltado de `2px` usando el color del tipo de alerta:
     - Información/Info: `ACCENT_BLUE` (`#005a82`)
     - Éxito/Success: `ACCENT_GREEN` (`#0acbe6`)
     - Advertencia/Warning: `ACCENT_YELLOW` (`#785a28`)
     - Error/Critical: `ACCENT_RED` (`#c83232`)
   - **Texto:** El cuerpo del texto debe ser `FG_TEXT` (`#f0e6d2`) y las descripciones secundarias `FG_MUTED` (`#a09b8c`).

3. **Tipografía y Legibilidad:**
   - Usar la fuente `Segoe UI` (o `Outfit` si está instalada).
   - Título principal de la alerta en `bold` y tamaño `12`.
   - Texto del cuerpo en tamaño `10` con justificación izquierda (`justify="left"`) y ajuste de línea automático (`wraplength` de aproximadamente `320px` a `350px`).

4. **Interactividad Premium (Hover Effects):**
   - El botón de confirmación ("Aceptar"/"Sí") debe usar el color del tipo de alerta como fondo, texto oscuro (`#11111b`), sin bordes, y cambiar dinámicamente de tonalidad (oscurecerse un 15%) al hacer hover (`<Enter>` y `<Leave>`).
   - El botón de cierre rápido `✕` en el título debe cambiar a color rojo al posicionar el cursor sobre él.

---

## 💻 Patrones de Código Recomendados

Para alertas de una sola opción, usa la clase existente `PremiumMessageBox` en [app_gui.py](file:///c:/Users/Administrador/Desktop/python/solicitud_almuerzo_auto/app_gui.py). Para confirmaciones de doble opción (Sí/No), usa `PremiumConfirmBox`.

### Ejemplo de Estilo para Popups Personalizados (Tkinter `tk.Toplevel`):
```python
class CustomPremiumPopup(tk.Toplevel):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG_MAIN)
        self.overrideredirect(True) # Quita el borde feo nativo del OS
        
        # Borde exterior coloreado
        border_frame = tk.Frame(self, bg=ACCENT, bd=2)
        border_frame.pack(fill="both", expand=True)
        
        inner_frame = tk.Frame(border_frame, bg=BG_CARD, padx=20, pady=20)
        inner_frame.pack(fill="both", expand=True)
        
        # ... Insertar Widgets estilizados ...
```

---

## 🔕 Notificaciones de Escritorio (Toasts)

Al interactuar con Toast notifications locales en Windows:
- Siempre usar bloques `try/except` robustos.
- La notificación nativa debe servir como alerta de segundo plano rápido, pero si la aplicación está en primer plano o abierta, se debe complementar o preferir el uso de `PremiumMessageBox` para una experiencia inmersiva e integrada con el tema del bot.
