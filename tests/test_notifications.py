import os
import pytest
from unittest.mock import patch, MagicMock
from src.notifications import send_windows_toast, send_telegram_message, send_telegram_photo

@patch('plyer.notification.notify')
def test_send_windows_toast(mock_notify):
    """Prueba que send_windows_toast llama a plyer con los parámetros adecuados."""
    send_windows_toast("Test Title", "Test Message")
    
    mock_notify.assert_called_once()
    _, kwargs = mock_notify.call_args
    assert kwargs['title'] == "Test Title"
    assert kwargs['message'] == "Test Message"
    assert kwargs['app_name'] == "SiGCABot"


@patch('plyer.notification.notify', side_effect=Exception("Plyer error"))
def test_send_windows_toast_handles_exception(mock_notify):
    """Prueba que las excepciones de la notificación de plyer se capturen de forma segura."""
    try:
        send_windows_toast("Test Title", "Test Message")
    except Exception as e:
        pytest.fail(f"send_windows_toast arrojó una excepción no controlada: {e}")


@patch('urllib.request.urlopen')
def test_send_telegram_message_success(mock_urlopen):
    """Prueba el envío exitoso de un mensaje de Telegram (mockeando el request HTTP)."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"ok": true}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = send_telegram_message("12345:token", "98765432", "Hello World")
    assert result is True
    mock_urlopen.assert_called_once()


def test_send_telegram_message_missing_credentials():
    """Prueba que el envío de mensaje de Telegram falla si no hay credenciales."""
    result = send_telegram_message(None, None, "Hello World")
    assert result is False


@patch('urllib.request.urlopen', side_effect=Exception("Connection refused"))
def test_send_telegram_message_failure(mock_urlopen):
    """Prueba que el envío a Telegram maneja correctamente fallos de red/conexión."""
    result = send_telegram_message("12345:token", "98765432", "Hello World")
    assert result is False


@patch('urllib.request.urlopen')
@patch('os.path.exists', return_value=True)
@patch('builtins.open')
def test_send_telegram_photo_success(mock_open, mock_exists, mock_urlopen):
    """Prueba el envío exitoso de una foto a Telegram."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"ok": true}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Mock del archivo binario
    mock_file = MagicMock()
    mock_file.read.return_value = b"fake png data"
    mock_open.return_value.__enter__.return_value = mock_file

    result = send_telegram_photo("12345:token", "98765432", "dummy_path.png", "Caption text")
    assert result is True
    mock_urlopen.assert_called_once()


def test_send_telegram_photo_missing_inputs():
    """Prueba que el envío de fotos a Telegram falle con parámetros vacíos o inválidos."""
    result = send_telegram_photo(None, None, None)
    assert result is False


@patch('smtplib.SMTP_SSL')
def test_send_email_notification_success(mock_smtp):
    """Prueba el envío exitoso de correo electrónico vía SMTP de Gmail."""
    from src.notifications import send_email_notification
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    result = send_email_notification(
        to_email="corporativo@ex-cle.com",
        subject="Test Subject",
        body_html="<h1>Test</h1>",
        sender_email="johancarmino346@gmail.com",
        sender_password="app_password_test"
    )

    assert result is True
    mock_smtp.assert_called_once_with('smtp.gmail.com', 465, timeout=15)
    mock_server.login.assert_called_once_with("johancarmino346@gmail.com", "app_password_test")
    mock_server.send_message.assert_called_once()


def test_send_email_notification_missing_credentials():
    """Prueba que el envío de correo falle si no se configuran las credenciales SMTP."""
    from src.notifications import send_email_notification
    with patch('src.config.load_env_dict', return_value={}):
        result = send_email_notification(
            to_email="corporativo@ex-cle.com",
            subject="Test",
            body_html="<p>Test</p>",
            sender_email="",
            sender_password=""
        )
        assert result is False

