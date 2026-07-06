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
