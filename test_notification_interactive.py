# test_notification_interactive.py
# =============================================================================
# SiGCABot — Script de Prueba Interactivo de Notificación
# =============================================================================
# Importa la función de notificación modificada y lanza un toast para verificar
# que la librería plyer esté correctamente integrada y funcione de manera nativa.
# =============================================================================

import sys
import os

# Asegurar que la ruta base esté en el PYTHONPATH para importar desde src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.notifications import send_windows_toast

if __name__ == "__main__":
    print("[INFO] Lanzando notificacion Toast de prueba...")
    
    title = "SiGCABot — Prueba"
    message = "¡La integración de notificaciones nativas con plyer funciona correctamente!"
    
    send_windows_toast(title, message)
    
    print("[INFO] Notificacion enviada. Deberias ver un globo o toast de Windows en tu pantalla.")
