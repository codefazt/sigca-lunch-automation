import os
import json
import pytest
from datetime import time
from unittest.mock import patch, MagicMock

# Importar la clase LunchBot
# Usamos try/except para evitar fallas si lunch_bot aún no está completamente implementado (TDD estricto)
try:
    from src.bot_engine import LunchBot
except ImportError:
    LunchBot = None


def test_lunch_bot_class_exists():
    assert LunchBot is not None, "La clase LunchBot debe existir en src/bot_engine.py"


@pytest.fixture
def mock_env(tmp_path):
    # Crear un entorno controlado temporal
    config_data = {
      "start_hour": 15,
      "start_minute": 30,
      "end_hour": 10,
      "end_minute": 0,
      "timeout_ms": 10000,
      "headless": True,
      "retries": 1,
      "retry_delay_sec": 1
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    env_vars = {
      "SIGCA_USER": "johan.carmino@ex-cle.com",
      "SIGCA_PASSWORDS": "password1,password2",
      "SIGCA_URL": "https://sigca.ex-cle.com/"
    }

    env_file = tmp_path / ".env"
    env_file.write_text(
        "SIGCA_USER=johan.carmino@ex-cle.com\n"
        "SIGCA_PASSWORDS=password1,password2\n"
        "SIGCA_URL=https://sigca.ex-cle.com/\n"
    )

    with patch.dict(os.environ, env_vars), \
         patch("src.config.CONFIG_PATH", str(config_file)), \
         patch("src.config.ENV_PATH", str(env_file)), \
         patch("src.bot_engine.CONFIG_PATH", str(config_file)):
        yield


def test_is_time_valid(mock_env):
    bot = LunchBot()
    
    # Hora de inicio válida: 3:30 PM (15:30)
    assert bot.is_time_valid(time(15, 30)) is True
    
    # Hora válida en la tarde: 8:00 PM (20:00)
    assert bot.is_time_valid(time(20, 0)) is True
    
    # Hora válida antes de medianoche: 11:59 PM (23:59)
    assert bot.is_time_valid(time(23, 59)) is True
    
    # Hora válida en la madrugada: Midnight (0:00)
    assert bot.is_time_valid(time(0, 0)) is True
    
    # Hora límite superior válida: 9:59 AM (9:59)
    assert bot.is_time_valid(time(9, 59)) is True
    
    # Fuera de rango (demasiado temprano para la tarde): 3:29 PM (15:29)
    assert bot.is_time_valid(time(15, 29)) is False
    
    # Fuera de rango (demasiado tarde para la mañana): 10:00 AM (10:00)
    assert bot.is_time_valid(time(10, 0)) is False
    
    # Fuera de rango (tarde del día): 12:00 PM (12:00)
    assert bot.is_time_valid(time(12, 0)) is False


def test_load_credentials_success(mock_env):
    bot = LunchBot()
    assert bot.username == "johan.carmino@ex-cle.com"
    assert bot.passwords == ["password1", "password2"]
    assert bot.url == "https://sigca.ex-cle.com/"


def test_load_credentials_missing_user(tmp_path):
    env_vars = {
      "SIGCA_PASSWORDS": "password1",
      "SIGCA_URL": "https://sigca.ex-cle.com/"
    }
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SIGCA_PASSWORDS=password1\n"
        "SIGCA_URL=https://sigca.ex-cle.com/\n"
    )
    with patch.dict(os.environ, env_vars, clear=True), \
         patch("src.config.ENV_PATH", str(env_file)), \
         patch("src.config.CONFIG_PATH", str(tmp_path / "config.json")), \
         patch("src.bot_engine.CONFIG_PATH", str(tmp_path / "config.json")):
        with pytest.raises(ValueError, match="Falta la variable de entorno SIGCA_USER"):
            LunchBot()


def test_load_credentials_missing_passwords(tmp_path):
    env_vars = {
      "SIGCA_USER": "johan.carmino@ex-cle.com",
      "SIGCA_URL": "https://sigca.ex-cle.com/"
    }
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SIGCA_USER=johan.carmino@ex-cle.com\n"
        "SIGCA_URL=https://sigca.ex-cle.com/\n"
    )
    with patch.dict(os.environ, env_vars, clear=True), \
         patch("src.config.ENV_PATH", str(env_file)), \
         patch("src.config.CONFIG_PATH", str(tmp_path / "config.json")), \
         patch("src.bot_engine.CONFIG_PATH", str(tmp_path / "config.json")):
        with pytest.raises(ValueError, match="Falta la variable de entorno SIGCA_PASSWORDS"):
            LunchBot()


# ---------------------------------------------------------------------------
# Tests para get_target_lunch_date (Ciclo Operativo de Almuerzo)
# ---------------------------------------------------------------------------

from datetime import datetime, date
from src.config import get_target_lunch_date


# Configuración por defecto: ventana que cruza medianoche (15:30 a 10:00)
CROSS_MIDNIGHT_CONFIG = {
    "start_hour": 15, "start_minute": 30,
    "end_hour": 10, "end_minute": 0
}

# Configuración de ventana en el mismo día (07:30 a 10:00)
SAME_DAY_CONFIG = {
    "start_hour": 7, "start_minute": 30,
    "end_hour": 10, "end_minute": 0
}


def test_target_lunch_date_afternoon_tuesday():
    """Martes 3:30 PM → almuerzo es para el Miércoles."""
    now = datetime(2026, 7, 21, 15, 30)  # Martes 3:30 PM
    target, day_name = get_target_lunch_date(now=now, config=CROSS_MIDNIGHT_CONFIG)
    assert target == date(2026, 7, 22)
    assert day_name == "Miércoles"


def test_target_lunch_date_late_evening_tuesday():
    """Martes 11:59 PM → almuerzo sigue siendo para el Miércoles."""
    now = datetime(2026, 7, 21, 23, 59)  # Martes 11:59 PM
    target, day_name = get_target_lunch_date(now=now, config=CROSS_MIDNIGHT_CONFIG)
    assert target == date(2026, 7, 22)
    assert day_name == "Miércoles"


def test_target_lunch_date_midnight_wednesday():
    """Miércoles 00:01 AM → almuerzo sigue siendo para el Miércoles (mismo ciclo)."""
    now = datetime(2026, 7, 22, 0, 1)  # Miércoles 00:01 AM
    target, day_name = get_target_lunch_date(now=now, config=CROSS_MIDNIGHT_CONFIG)
    assert target == date(2026, 7, 22)
    assert day_name == "Miércoles"


def test_target_lunch_date_early_morning_wednesday():
    """Miércoles 9:59 AM → almuerzo sigue siendo para el Miércoles (mismo ciclo)."""
    now = datetime(2026, 7, 22, 9, 59)  # Miércoles 9:59 AM
    target, day_name = get_target_lunch_date(now=now, config=CROSS_MIDNIGHT_CONFIG)
    assert target == date(2026, 7, 22)
    assert day_name == "Miércoles"


def test_target_lunch_date_gap_between_end_and_start():
    """Miércoles 12:00 PM (fuera de ventana) → target es Jueves (próximo ciclo)."""
    now = datetime(2026, 7, 22, 12, 0)  # Miércoles 12:00 PM
    target, day_name = get_target_lunch_date(now=now, config=CROSS_MIDNIGHT_CONFIG)
    assert target == date(2026, 7, 23)
    assert day_name == "Jueves"


def test_target_lunch_date_exactly_at_end():
    """Miércoles 10:00 AM (fin exacto de ventana) → target es Jueves (próximo ciclo)."""
    now = datetime(2026, 7, 22, 10, 0)  # Miércoles 10:00 AM
    target, day_name = get_target_lunch_date(now=now, config=CROSS_MIDNIGHT_CONFIG)
    assert target == date(2026, 7, 23)
    assert day_name == "Jueves"


def test_target_lunch_date_wednesday_afternoon():
    """Miércoles 3:30 PM → almuerzo para el Jueves (nuevo ciclo)."""
    now = datetime(2026, 7, 22, 15, 30)  # Miércoles 3:30 PM
    target, day_name = get_target_lunch_date(now=now, config=CROSS_MIDNIGHT_CONFIG)
    assert target == date(2026, 7, 23)
    assert day_name == "Jueves"


def test_target_lunch_date_same_day_window_before_start():
    """Con ventana 07:30-10:00 (mismo día), a las 05:00 AM → target es hoy."""
    now = datetime(2026, 7, 22, 5, 0)
    target, day_name = get_target_lunch_date(now=now, config=SAME_DAY_CONFIG)
    # Antes de la ventana y antes del cierre? No, 05:00 < 07:30 y 05:00 < 10:00
    # Dentro de la rama start <= end: current_t < start_t, y current_t < end_t → target = hoy
    assert target == date(2026, 7, 22)


def test_target_lunch_date_same_day_window_during():
    """Con ventana 07:30-10:00, a las 08:00 AM → target es mañana."""
    now = datetime(2026, 7, 22, 8, 0)
    target, day_name = get_target_lunch_date(now=now, config=SAME_DAY_CONFIG)
    # current_t >= start_t → target = mañana
    assert target == date(2026, 7, 23)


def test_target_lunch_date_same_day_window_after_close():
    """Con ventana 07:30-10:00, a las 14:00 → target es mañana (fuera de ventana)."""
    now = datetime(2026, 7, 22, 14, 0)
    target, day_name = get_target_lunch_date(now=now, config=SAME_DAY_CONFIG)
    # current_t >= start_t → target = mañana
    assert target == date(2026, 7, 23)


def test_disabled_day_maps_to_target_lunch_date():
    """Marcar 'Jueves' como excluido bloquea pedidos desde la tarde del Miércoles."""
    disabled_days = ["Jueves"]
    # Miércoles 4:00 PM → target es Jueves
    now = datetime(2026, 7, 22, 16, 0)
    target, day_name = get_target_lunch_date(now=now, config=CROSS_MIDNIGHT_CONFIG)
    assert day_name == "Jueves"
    assert day_name in disabled_days

    # Jueves 8:00 AM → target sigue siendo Jueves (mismo ciclo nocturno)
    now2 = datetime(2026, 7, 23, 8, 0)
    target2, day_name2 = get_target_lunch_date(now=now2, config=CROSS_MIDNIGHT_CONFIG)
    assert day_name2 == "Jueves"
    assert day_name2 in disabled_days

    # Jueves 4:00 PM → target es Viernes (nuevo ciclo, no bloqueado)
    now3 = datetime(2026, 7, 23, 16, 0)
    target3, day_name3 = get_target_lunch_date(now=now3, config=CROSS_MIDNIGHT_CONFIG)
    assert day_name3 == "Viernes"
    assert day_name3 not in disabled_days
