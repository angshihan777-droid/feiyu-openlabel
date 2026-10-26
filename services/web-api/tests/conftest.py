import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("FY_CONFIG_FILE", str(ROOT / "config" / "feiyu-ci.yaml"))
os.environ.setdefault(
    "FY_JWT_SECRET", "test-secret-012345678901234567890123"
)
