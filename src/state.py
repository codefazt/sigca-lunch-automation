"""
Variables de estado global compartidas entre hilos.
Módulo separado para evitar dependencias circulares entre componentes.
"""

# Flag global para detener todos los hilos en segundo plano al cerrar la app
stop_threads = False
