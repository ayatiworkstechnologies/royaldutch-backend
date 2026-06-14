import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.rate_limit import clear_rate_limits
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def reset_test_runtime(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("RUN_STARTUP_SEEDERS", "true")
    monkeypatch.setenv("ENABLE_IN_PROCESS_WORKER", "false")
    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()
    clear_rate_limits()
    yield
    clear_rate_limits()
    get_settings.cache_clear()
