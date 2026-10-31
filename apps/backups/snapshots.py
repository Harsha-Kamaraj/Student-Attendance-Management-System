"""Versioned logical snapshots of managed PostgreSQL tables; no SQL comes from a file.

Restore replaces application/auth data atomically, merges append-only audit history,
and excludes runtime sessions plus the backup catalogue/schedule. Future installed
application tables are included automatically; migrations must match exactly.
"""

import json
import uuid

from django.apps import apps
from django.conf import settings
from django.contrib.auth.hashers import is_password_usable
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.debug import sensitive_variables

from apps.accounts.models import Role, User
from apps.audit.models import AuditEntry

from .locks import BackupError

FORMAT_VERSION = 1
AUDIT_TABLE = AuditEntry._meta.db_table


def table_models():
    return {
        model._meta.db_table: model
        for model in apps.get_models(include_auto_created=True)
        if model._meta.managed
        and not model._meta.proxy
        and model._meta.app_label not in {"backups", "sessions"}
    }


def schema():
    return {
        table: [
            [field.column, field.db_type(connection), field.null, field.primary_key]
            for field in model._meta.local_fields
        ]
        for table, model in sorted(table_models().items())
    }


def migrations():
    return [list(item) for item in sorted(MigrationRecorder(connection).applied_migrations())]


def lock_tables(*, restore=False):
    tables = set(table_models())
    if restore:
        tables.add(Session._meta.db_table)
    names = ", ".join(connection.ops.quote_name(name) for name in sorted(tables))
    mode = "ACCESS EXCLUSIVE" if restore else "SHARE"
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('lock_timeout', %s, true)", [f"{settings.BACKUP_LOCK_TIMEOUT_SECONDS}s"]
        )
        cursor.execute(f"LOCK TABLE {names} IN {mode} MODE")


@sensitive_variables()
def capture():
    """Caller holds transaction and table locks for a coherent multi-table snapshot."""
    payload = {
        "application": "student-attendance",
        "version": FORMAT_VERSION,
        "created_at": timezone.now().isoformat(),
        "migrations": migrations(),
        "schema": schema(),
        "tables": {},
    }
    total = 0
    for table, model in sorted(table_models().items()):
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT row_to_json(t)::text FROM {quote(table)} t ORDER BY {quote(model._meta.pk.column)}"
            )
            rows = []
            while chunk := cursor.fetchmany(1000):
                for (raw,) in chunk:
                    total += len(raw.encode("utf-8"))
                    if total > settings.BACKUP_MAX_BYTES:
                        raise BackupError(
                            "The backup exceeds the configured size limit. No backup was replaced."
                        )
                    rows.append(json.loads(raw))
        payload["tables"][table] = rows
    validate(payload)
    return payload


@sensitive_variables()
def validate(payload):
    """Reject foreign formats, schema changes, malformed rows, and unusable account snapshots."""
    invalid = "This backup is corrupt or incompatible with the current application schema."
    if not isinstance(payload, dict):
        raise BackupError(invalid)
    if (
        payload.get("application") != "student-attendance"
        or payload.get("version") != FORMAT_VERSION
        or payload.get("schema") != schema()
        or payload.get("migrations") != migrations()
    ):
        raise BackupError(invalid)
    try:
        created = parse_datetime(payload["created_at"])
        if created is None or timezone.is_naive(created):
            raise ValueError
        tables = payload["tables"]
        if not isinstance(tables, dict) or set(tables) != set(table_models()):
            raise ValueError
        for table, model in table_models().items():
            rows = tables[table]
            columns = {field.column for field in model._meta.local_fields}
            if not isinstance(rows, list):
                raise ValueError
            ids = set()
            for row in rows:
                if not isinstance(row, dict) or set(row) != columns:
                    raise ValueError
                pk = row[model._meta.pk.column]
                if type(pk) is not int or pk <= 0 or pk in ids:
                    raise ValueError
                ids.add(pk)
        users = tables[User._meta.db_table]
        if not any(
            row["role"] == Role.ADMIN and row["is_active"] is True and is_password_usable(row["password"])
            for row in users
        ):
            raise BackupError("The backup must contain an active Admin account with a usable password.")
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise BackupError(invalid) from error


def row_counts(payload):
    return {table: len(rows) for table, rows in payload["tables"].items()}


@sensitive_variables()
def _insert_rows(table, rows):
    quote = connection.ops.quote_name
    # Use the driver's cursor for decrypted data so Django DEBUG query logging never
    # records account hashes, authenticator secrets or personal data as SQL parameters.
    with connection.wrap_database_errors, connection.connection.cursor() as cursor:
        for start in range(0, len(rows), 1000):
            cursor.execute(
                f"INSERT INTO {quote(table)} SELECT * FROM json_populate_recordset(NULL::{quote(table)}, %s)",
                [json.dumps(rows[start : start + 1000])],
            )


@sensitive_variables()
def _merge_audit(rows):
    """Keep every live entry; append only snapshot events whose full content is missing."""
    quote = connection.ops.quote_name
    table = quote(AUDIT_TABLE)
    columns = [f.column for f in AuditEntry._meta.local_fields if not f.primary_key]
    names = ", ".join(quote(name) for name in columns)
    values = ", ".join(f"incoming.{quote(name)}" for name in columns)
    with connection.wrap_database_errors, connection.connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {table} ({names}) SELECT {values} "
            f"FROM json_populate_recordset(NULL::{table}, %s) incoming "
            f"WHERE NOT EXISTS (SELECT 1 FROM {table} existing "
            "WHERE (to_jsonb(existing) - 'id') = (to_jsonb(incoming) - 'id'))",
            [json.dumps(rows)],
        )


@sensitive_variables()
def replace(payload):
    """Caller holds exclusive maintenance/table locks and an atomic transaction.

    Constraints are checked before commit. No triggers are disabled, no schema is
    loaded from a file, and no SQL from a backup is executed.
    """
    validate(payload)
    models = table_models()
    tables = sorted(set(models) - {AUDIT_TABLE})
    quote = connection.ops.quote_name
    high_water = {}
    sequences = {}
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
        # Do not reuse IDs of post-backup records still referenced in the retained audit log.
        for table in tables:
            pk = quote(models[table]._meta.pk.column)
            cursor.execute(f"SELECT COALESCE(MAX({pk}), 0) FROM {quote(table)}")
            high_water[table] = cursor.fetchone()[0]
            cursor.execute(
                "SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.oid = pg_get_serial_sequence(%s, %s)::regclass",
                [table, models[table]._meta.pk.column],
            )
            sequence = cursor.fetchone()
            if sequence:
                name = ".".join(quote(part) for part in sequence)
                sequences[table] = name
                cursor.execute(f"SELECT last_value FROM {name}")
                high_water[table] = max(high_water[table], cursor.fetchone()[0])
        names = ", ".join(quote(table) for table in [*tables, Session._meta.db_table])
        cursor.execute(f"TRUNCATE {names} RESTRICT")
    for table in tables:
        _insert_rows(table, payload["tables"][table])
    _merge_audit(payload["tables"][AUDIT_TABLE])

    # Restoring security state must never revive an authenticated session or a single-use code.
    User.objects.update(otp_reset_token=uuid.uuid4())
    now = timezone.now()
    User.objects.filter(otp_confirmed=True).update(otp_last_step=int(now.timestamp()) // 30)
    from apps.accounts.models import OTPBackupCode, OTPEmailCode

    OTPEmailCode.objects.all().delete()
    OTPBackupCode.objects.filter(used_at__isnull=True).update(used_at=now)

    # ALTER SEQUENCE is transactional; setval() would survive a rollback and risk duplicate IDs.
    with connection.cursor() as cursor:
        for table in tables:
            pk_column = models[table]._meta.pk.column
            cursor.execute(f"SELECT COALESCE(MAX({quote(pk_column)}), 0) FROM {quote(table)}")
            next_id = max(high_water[table], cursor.fetchone()[0]) + 1
            if name := sequences.get(table):
                cursor.execute(f"ALTER SEQUENCE {name} RESTART WITH {int(next_id)}")
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
    ContentType.objects.clear_cache()
