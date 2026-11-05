import pytest

from config import ConfigError, load_settings, parse_admins

BASE = {
    "BOT_TOKEN": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
    "DATABASE_URL": "postgresql://u:p@host:5432/postgres",
    "ADMINS": "111:محمد,222:حسام",
}


def test_valid_settings():
    s = load_settings(dict(BASE))
    assert [a.user_id for a in s.admins] == [111, 222]
    assert s.schema_prod == "els962" and s.schema_test == "els962_test"
    assert s.port is None


def test_secrets_hidden_in_repr():
    assert "ABCDEFGHIJ" not in repr(load_settings(dict(BASE)))
    assert "u:p@" not in repr(load_settings(dict(BASE)))


@pytest.mark.parametrize("missing", ["BOT_TOKEN", "DATABASE_URL", "ADMINS"])
def test_missing_required(missing):
    env = dict(BASE)
    del env[missing]
    with pytest.raises(ConfigError):
        load_settings(env)


@pytest.mark.parametrize("raw", ["111", "abc:محمد", "111:", "111:a,111:b", "1:a,2:b,3:c", "0:a"])
def test_bad_admins(raw):
    with pytest.raises(ConfigError):
        parse_admins(raw)


def test_public_schema_rejected():
    with pytest.raises(ConfigError):
        load_settings({**BASE, "DB_SCHEMA_PROD": "public"})


def test_same_schema_rejected():
    with pytest.raises(ConfigError):
        load_settings({**BASE, "DB_SCHEMA_PROD": "abc", "DB_SCHEMA_TEST": "abc"})


def test_bad_database_url():
    with pytest.raises(ConfigError):
        load_settings({**BASE, "DATABASE_URL": "mysql://x"})
