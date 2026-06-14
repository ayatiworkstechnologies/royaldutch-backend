from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine
from scripts.verify_schema_for_stamp import main as verify_schema


def main() -> int:
    inspector = inspect(engine)
    if "alembic_version" in inspector.get_table_names():
        print("Database already has alembic_version. No stamp needed.")
        return 0

    result = verify_schema()
    if result != 0:
        return result

    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")
    print("Stamped existing schema at Alembic head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
