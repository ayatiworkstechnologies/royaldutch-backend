import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, text=True)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def validate_single_head() -> None:
    config = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    if len(heads) != 1:
        raise SystemExit(f"Expected exactly one Alembic head, found {heads}")
    print(f"alembic_head={heads[0]}")


def main() -> None:
    validate_single_head()
    run([sys.executable, "-m", "alembic", "upgrade", "head"])
    if os.getenv("STRICT_MIGRATION_CHECK", "").lower() in {"1", "true", "yes"}:
        run([sys.executable, "-m", "alembic", "check"])
    print("migration_validation=ok")


if __name__ == "__main__":
    main()
