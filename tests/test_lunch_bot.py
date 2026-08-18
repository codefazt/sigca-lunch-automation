import os
import json
import pytest
from datetime import time
from unittest.mock import patch, MagicMock

# Importar la clase LunchBot
# Usamos try/except para evitar fallas si lunch_bot aún no está completamente implementado (TDD estricto)
try:
    from src.bot_engine import LunchBot, is_confirmed_order_result, _fill_login_field
except ImportError:
    LunchBot = None
    is_confirmed_order_result = None
    _fill_login_field = None


def test_lunch_bot_class_exists():
    assert LunchBot is not None, "La clase LunchBot debe existir en src/bot_engine.py"


def test_confirmed_order_result_classification():
    assert is_confirmed_order_result(0, "Solicitud exitosa: Solicitud confirmada.") is True
    assert is_confirmed_order_result(0, "El almuerzo ya ha sido solicitado para hoy/mañana.") is True
    assert is_confirmed_order_result(0, "Fuera de horario de ejecución.") is False
    assert is_confirmed_order_result(0, "No se detectó el mensaje de éxito después de enviar.") is False
    assert is_confirmed_order_result(0, "[DRY RUN] Simulación completada.", dry_run=True) is False


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


def test_save_env_password_candidates_round_trip(tmp_path):
    from src.config import load_env_dict, save_env_values

    env_file = tmp_path / ".env"
    with patch("src.config.ENV_PATH", str(env_file)):
        save_env_values({
            "SIGCA_USER": "user@example.com",
            "SIGCA_PASSWORDS": "Johan2022.,johan2022."
        })

        loaded = load_env_dict()
        raw = env_file.read_text(encoding="utf-8")

    assert loaded["SIGCA_PASSWORDS"] == "Johan2022.,johan2022."
    assert "SIGCA_PASSWORDS=Johan2022.,johan2022." not in raw


def test_fill_login_field_retries_when_programmatic_value_is_cleared():
    class FakeLoginField:
        def __init__(self):
            self.value = ""

        def fill(self, value):
            self.value = ""

        def input_value(self):
            return self.value

        def click(self):
            pass

        def press(self, key):
            self.value = ""

        def type(self, value, delay=0):
            self.value = value

    field = FakeLoginField()

    assert _fill_login_field(field, "Johan2022.", "contraseña") is True
    assert field.value == "Johan2022."


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


# ---------------------------------------------------------------------------
# Tests para Auto-Healing de Inicio con Windows (set_startup & repair)
# ---------------------------------------------------------------------------

from src.config import get_expected_startup_command, check_and_repair_startup


def test_get_expected_startup_command():
    """Verifica que el comando de auto-inicio retorne una cadena no vacía entre comillas."""
    cmd = get_expected_startup_command()
    assert isinstance(cmd, str)
    assert cmd.startswith('"') and cmd.endswith('"') or '"' in cmd


def test_check_and_repair_startup_runs_without_crash(tmp_path):
    """Verifica que check_and_repair_startup se ejecute sin excepciones."""
    status_file = tmp_path / "status.json"
    status_file.write_text('{"startup_on_boot": false}')
    with patch("src.config.STATUS_PATH", str(status_file)):
        res = check_and_repair_startup()
        assert isinstance(res, bool)


def test_save_status_writes_valid_json(tmp_path):
    from src.config import save_status

    status_file = tmp_path / "status.json"
    data = {"is_active": True, "last_run_status": "success"}

    with patch("src.config.STATUS_PATH", str(status_file)):
        save_status(data)

    assert json.loads(status_file.read_text(encoding="utf-8")) == data


# ---------------------------------------------------------------------------
# Tests para fill_form_field (Estrellas Angular y Campos Dinámicos)
# ---------------------------------------------------------------------------

def test_fill_form_field_rating_with_title(mock_env):
    bot = LunchBot()
    
    mock_page = MagicMock()
    mock_container = MagicMock()
    mock_star_loc = MagicMock()
    mock_star_loc.count.return_value = 1
    mock_star_loc.first.is_visible.return_value = True
    
    # Simular que el locator por selector devuelve el contenedor y el botón de estrella
    mock_page.locator.return_value = mock_container
    mock_container.count.return_value = 1
    mock_container.nth.return_value = mock_container
    mock_container.locator.side_effect = lambda sel: mock_star_loc if "button" in sel else MagicMock(count=lambda: 1)
    
    res = bot.fill_form_field(mock_page, "¿Te gustó el almuerzo", "rating", "3")
    assert res is True
    mock_star_loc.first.click.assert_called_once()


def test_fill_form_field_rating_with_index(mock_env):
    bot = LunchBot()
    
    mock_page = MagicMock()
    mock_container = MagicMock()
    mock_title_loc = MagicMock(count=lambda: 0)
    
    mock_star_btn_1 = MagicMock()
    mock_star_btn_2 = MagicMock()
    mock_star_btn_3 = MagicMock()
    mock_buttons_loc = MagicMock()
    mock_buttons_loc.count.return_value = 5
    mock_buttons_loc.nth.side_effect = lambda idx: [mock_star_btn_1, mock_star_btn_2, mock_star_btn_3][idx]
    
    mock_page.locator.return_value = mock_container
    mock_container.count.return_value = 1
    mock_container.nth.return_value = mock_container
    
    def container_locator(sel):
        if "title^='3 de'" in sel or "title*='3 de 5'" in sel:
            return mock_title_loc
        if "rq-star" in sel or "radiogroup" in sel:
            return mock_buttons_loc
        return MagicMock(count=lambda: 1)
        
    mock_container.locator.side_effect = container_locator
    
    res = bot.fill_form_field(mock_page, "¿Te gustó el almuerzo", "rating", "3")
    assert res is True
    mock_star_btn_3.click.assert_called_once()


def test_fill_form_field_select_with_events(mock_env):
    bot = LunchBot()
    
    mock_page = MagicMock()
    mock_container = MagicMock()
    mock_select = MagicMock()
    mock_select.count.return_value = 1
    mock_select.is_visible.return_value = True
    mock_select.evaluate.return_value = "select"
    
    mock_page.locator.return_value = mock_container
    mock_container.count.return_value = 1
    mock_container.nth.return_value = mock_container
    mock_container.locator.return_value = mock_select
    mock_select.first = mock_select
    
    res = bot.fill_form_field(mock_page, "Ubicación", "select", "Sede ExCle")
    assert res is True
    mock_select.select_option.assert_called_with(label="Sede ExCle")
    assert mock_select.dispatch_event.call_count >= 1

