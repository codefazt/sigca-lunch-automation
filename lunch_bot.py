"""
SiGCABot — CLI (Interfaz de Línea de Comandos) para el motor de automatización.

Este archivo es un wrapper fino para ejecutar el bot directamente desde la terminal
sin necesidad de la interfaz gráfica. Útil para pruebas de desarrollador y
ejecuciones programadas vía run_job.bat.

Uso:
    python lunch_bot.py                  → Ejecuta el bot normalmente
    python lunch_bot.py --dry-run        → Simulación (no confirma el pedido)
    python lunch_bot.py --force-time     → Ignora la validación del rango horario
    python lunch_bot.py --dry-run --force-time  → Ambas opciones combinadas
"""

import sys
import argparse

# Importar módulos del paquete src
from src.logger import logger
from src.bot_engine import LunchBot


def main():
    parser = argparse.ArgumentParser(
        description="Bot automatizado para pedir almuerzo en SiGCA."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Ejecuta todo el flujo (incluyendo login) pero no confirma el pedido."
    )
    parser.add_argument(
        "--force-time", action="store_true",
        help="Ignora la validación del rango de hora local."
    )
    args = parser.parse_args()

    logger.info("Iniciando ejecución de LunchBot (CLI)...")
    try:
        bot = LunchBot()
        if args.force_time:
            bot.is_time_valid = lambda *a, **k: True
            logger.info("Validación horaria forzada (desactivada).")

        res = bot.run_automation(dry_run=args.dry_run)
        if isinstance(res, tuple):
            exit_code, msg, evidence = res
        else:
            exit_code, msg, evidence = res, "Completado", None

        logger.info(f"Ejecución completada: {msg} (código: {exit_code})")
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"Error crítico no controlado al ejecutar LunchBot: {e}", exc_info=True)
        sys.exit(5)


if __name__ == "__main__":
    main()
