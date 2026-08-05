"""
Bloqueo de archivo compartido para evitar ejecuciones simultaneas.

El planificador de la GUI, el Programador de Tareas de Windows y los comandos
manuales pueden iniciar procesos independientes. Este bloqueo evita que dos de
ellos naveguen y envien una solicitud al mismo tiempo.
"""

import logging
import os
from contextlib import contextmanager

from src.config import BASE_DIR

logger = logging.getLogger("SiGCABot")

LOCK_PATH = os.path.join(BASE_DIR, ".lunch_automation.lock")


@contextmanager
def acquire_job_lock():
    """Adquiere un bloqueo no bloqueante y lo libera al salir del contexto.

    En Windows se usa ``msvcrt`` porque el bloqueo se libera automaticamente
    si el proceso termina de forma inesperada. En otros sistemas se utiliza
    ``fcntl`` para mantener el mismo comportamiento durante las pruebas.
    """
    lock_file = None
    acquired = False

    try:
        lock_file = open(LOCK_PATH, "a+", encoding="ascii")

        # msvcrt.locking necesita que exista al menos un byte en el archivo.
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write("0")
            lock_file.flush()
        lock_file.seek(0)

        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        acquired = True
        yield True
    except (OSError, IOError):
        logger.warning("Ya existe otra automatizacion de almuerzo en ejecucion. Omitiendo este proceso.")
        yield False
    finally:
        if lock_file is not None:
            if acquired:
                try:
                    lock_file.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except (OSError, IOError):
                    pass
            try:
                lock_file.close()
            except Exception:
                pass
