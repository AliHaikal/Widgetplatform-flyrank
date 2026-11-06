"""Shared requirement: real persistence (schema as migrations, indexes, seed)."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from tests.conftest import ROOT, auth


def _alembic_config(db_path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def test_migrations_build_the_schema_with_indexes_and_the_idempotency_constraint(tmp_path):
    db = tmp_path / "fresh.db"
    command.upgrade(_alembic_config(db), "head")

    inspector = inspect(create_engine(f"sqlite:///{db}"))
    assert {"widgets", "submissions", "alembic_version"} <= set(inspector.get_table_names())

    widget_indexes = {i["name"] for i in inspector.get_indexes("widgets")}
    submission_indexes = {i["name"] for i in inspector.get_indexes("submissions")}
    assert "ix_widgets_tenant_created" in widget_indexes
    assert {"ix_submissions_widget_created", "ix_submissions_tenant_widget_created"} <= submission_indexes

    uniques = {u["name"] for u in inspector.get_unique_constraints("submissions")}
    assert "uq_submissions_widget_idempotency" in uniques


def test_migrations_match_the_models_exactly(tmp_path):
    """Fails if someone changes models.py without writing a migration."""
    config = _alembic_config(tmp_path / "check.db")
    command.upgrade(config, "head")
    command.check(config)


def test_migrations_can_be_rolled_back(tmp_path):
    db = tmp_path / "down.db"
    config = _alembic_config(db)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    tables = set(inspect(create_engine(f"sqlite:///{db}")).get_table_names())
    assert "widgets" not in tables and "submissions" not in tables


def test_seed_is_idempotent_and_the_demo_tokens_work(client):
    from scripts.seed import seed

    first = {w.id for w in seed()}
    second = {w.id for w in seed()}
    assert first == second and len(first) == 3

    a = client.get("/widgets", headers=auth("tenant-a")).json()
    b = client.get("/widgets", headers=auth("tenant-b")).json()
    assert len(a) == 2 and len(b) == 1
    assert {w["type"] for w in a} == {"signup_form", "cta_popover"}
