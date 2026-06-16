import os
from pathlib import Path
from tempfile import gettempdir

TEST_DB = Path(gettempdir()) / "atlas-api-tests.sqlite3"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["ATLAS_STORAGE_PATH"] = str(TEST_DB)
os.environ["ATLAS_ARTIFACT_DIR"] = str(Path(gettempdir()) / "atlas-api-artifacts")
