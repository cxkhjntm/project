"""Test structured logging configuration."""

from app.utils.logger import get_logger, mask_sensitive_data, setup_logging


def test_mask_api_key_in_string_value():
    event_dict = {"message": "Called API with sk-abc12345xyz successfully"}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["message"] == "Called API with sk-abc12345*** successfully"


def test_mask_password_by_key_name():
    event_dict = {"password": "secret123", "event": "login"}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["password"] == "***MASKED***"
    assert result["event"] == "login"


def test_mask_token_by_key_name():
    event_dict = {"token": "bearer_xyz", "event": "auth"}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["token"] == "***MASKED***"
    assert result["event"] == "auth"


def test_mask_secret_by_key_name():
    event_dict = {"secret": "my_secret_value", "event": "config"}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["secret"] == "***MASKED***"
    assert result["event"] == "config"


def test_mask_api_key_by_key_name():
    event_dict = {"api_key": "sk-abc12345xyz", "event": "request"}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["api_key"] == "***MASKED***"
    assert result["event"] == "request"


def test_mask_authorization_by_key_name():
    event_dict = {"authorization": "Bearer token123", "event": "request"}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["authorization"] == "***MASKED***"
    assert result["event"] == "request"


def test_do_not_mask_normal_values():
    event_dict = {"name": "John", "age": "30", "city": "Tokyo"}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["name"] == "John"
    assert result["age"] == "30"
    assert result["city"] == "Tokyo"


def test_do_not_mask_non_string_values():
    event_dict = {"count": 42, "active": True, "items": [1, 2, 3]}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["count"] == 42
    assert result["active"] is True
    assert result["items"] == [1, 2, 3]


def test_mask_case_insensitive_keys():
    event_dict = {"API_KEY": "value1", "Password": "value2", "TOKEN": "value3"}
    result = mask_sensitive_data(None, None, event_dict)
    assert result["API_KEY"] == "***MASKED***"
    assert result["Password"] == "***MASKED***"
    assert result["TOKEN"] == "***MASKED***"


def test_setup_logging_debug_mode():
    setup_logging(debug=True)
    logger = get_logger("test")
    assert logger is not None


def test_setup_logging_production_mode():
    setup_logging(debug=False)
    logger = get_logger("test")
    assert logger is not None


def test_get_logger_returns_logger():
    logger = get_logger("test_module")
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")


def test_get_logger_different_names():
    logger1 = get_logger("module_a")
    logger2 = get_logger("module_b")
    assert logger1 is not None
    assert logger2 is not None
