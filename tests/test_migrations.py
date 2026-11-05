import re

import pytest

from database.migrations import MigrationError, discover_migrations


def test_discovers_foundation():
    migs = discover_migrations()
    assert migs and migs[0].version == 1 and migs[0].name == "foundation"


def test_checksum_stable():
    assert discover_migrations()[0].checksum == discover_migrations()[0].checksum


def test_no_destructive_statements():
    bad = re.compile(r"\bDROP\s+(TABLE|SCHEMA|DATABASE)\b|\bDELETE\s+FROM\b|\bpublic\.", re.I)
    for m in discover_migrations():
        assert not bad.search(m.sql_text), m.name


def test_gap_rejected(tmp_path):
    (tmp_path / "0001_a.sql").write_text("SELECT 1;")
    (tmp_path / "0003_c.sql").write_text("SELECT 1;")
    with pytest.raises(MigrationError):
        discover_migrations(tmp_path)


def test_bad_name_rejected(tmp_path):
    (tmp_path / "init.sql").write_text("SELECT 1;")
    with pytest.raises(MigrationError):
        discover_migrations(tmp_path)
