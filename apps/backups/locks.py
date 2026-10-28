"""Cross-worker PostgreSQL locks. Use direct/session-pooled database connections."""

from contextlib import contextmanager

from django.db import connection

MAINTENANCE_LOCK = 7262701
OPERATION_LOCK = 7262702


class BackupError(Exception):
    """A safe message suitable for the UI; never include database, path or secret details."""


class BackupBusy(BackupError):
    pass


@contextmanager
def database_lock(key, *, shared=False):
    suffix = "_shared" if shared else ""
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT pg_try_advisory_lock{suffix}(%s)", [key])
        acquired = cursor.fetchone()[0]
    if not acquired:
        raise BackupBusy("Another request or backup operation is active. Please try again shortly.")
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT pg_advisory_unlock{suffix}(%s)", [key])
