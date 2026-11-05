from datetime import datetime, timezone

import pytest

from database.schema_names import validate_schema_name
from services.security import get_admin, is_admin
from config import load_settings
from utils.logging_setup import redact
from utils.sanitize import sanitize
from utils.time import format_jordan, to_jordan


def test_jordan_time():
    dt = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    assert to_jordan(dt).hour == 15
    assert format_jordan(dt) == "2026-11-05 15:00"


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        to_jordan(datetime(2026, 1, 1))


def test_redact_token_in_url():
    token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    assert token not in redact(f"https://api.telegram.org/bot{token}/getMe")


def test_redact_db_password():
    out = redact("connect postgresql://user:SuperSecret@host/db failed")
    assert "SuperSecret" not in out and "user:" in out


def test_redact_pin():
    assert "5500" not in redact("pin=5500 entered")


def test_sanitize_nested():
    data = {"name": "x", "pin_hash": "h", "inner": {"password": "p", "ok": 1}, "l": [{"token": "t"}]}
    out = sanitize(data)
    assert out["pin_hash"] == "***" and out["inner"]["password"] == "***"
    assert out["inner"]["ok"] == 1 and out["l"][0]["token"] == "***" and out["name"] == "x"


@pytest.mark.parametrize("name", ["public", "auth", "Els962", "a", "pg_x", "els-962", "storage"])
def test_bad_schema_names(name):
    with pytest.raises(ValueError):
        validate_schema_name(name)


def test_admin_check_by_id_only():
    s = load_settings({"BOT_TOKEN": "1:x", "DATABASE_URL": "postgresql://a", "ADMINS": "111:محمد,222:حسام"})
    assert is_admin(s, 111) and is_admin(s, 222)
    assert not is_admin(s, 333) and not is_admin(s, 0)
    assert get_admin(s, 222).name == "حسام"
