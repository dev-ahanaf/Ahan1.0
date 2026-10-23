# tests use an isolated temporary database
import os
import tempfile

if "DATABASE_PATH" not in os.environ or "test" not in os.environ.get("DATABASE_PATH", ""):
    _db = tempfile.NamedTemporaryFile(prefix="myvoice-test-", suffix=".db", delete=False)
    _db.close()
    os.environ["DATABASE_PATH"] = _db.name

os.environ.setdefault("ADMIN_PASSWORD", "test-strong-admin-password")
os.environ.setdefault("ENROLLMENT_KEY", "test-strong-enrollment-key-123456")
