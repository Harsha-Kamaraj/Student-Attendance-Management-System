"""Admin backup/recovery and daily scheduling (BL-26, BL-27; SEC-20/22/26)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.dateparse import parse_datetime
from django.views.decorators.debug import sensitive_variables

from apps.accounts.models import Role, User
from apps.accounts.services import check_login
from apps.audit import services as audit

from . import snapshots, storage
from .locks import MAINTENANCE_LOCK, OPERATION_LOCK, BackupError, database_lock
from .models import Backup, BackupSchedule

IST = ZoneInfo("Asia/Kolkata")


def require_admin(actor):
    current = User.objects.filter(pk=getattr(actor, "pk", None), is_active=True, role=Role.ADMIN).first()
    if current is None:
        raise PermissionDenied("Only an active Admin may manage backups.")
    return current


def record_event(action, *, actor=None, backup=None, **kwargs):
    audit.record(
        action,
        actor=actor,
        actor_username="scheduler" if actor is None else "",
        target_type="Backup" if backup else "BackupSchedule",
        target_id=backup.pk if backup else 1,
        **kwargs,
    )


def recover_interrupted():
    # Called only while holding the operation lock: a running row then belongs to a dead worker.
    for backup in Backup.objects.filter(status=Backup.Status.RUNNING):
        backup.status = Backup.Status.FAILED
        backup.error = "The previous backup process was interrupted. Create a new backup."
        backup.completed_at = timezone.now()
        backup.save(update_fields=["status", "error", "completed_at"])
        record_event("backup.failure", backup=backup, new_value={"reason": "interrupted"})


@sensitive_variables()
def _store(payload, *, actor, kind, token=None):
    backup = Backup.objects.create(kind=kind, requested_by=actor.username if actor else "scheduler")
    try:
        token = storage.encrypt(payload) if token is None else token
        storage.publish(backup, token)
        with transaction.atomic():
            backup.status = Backup.Status.COMPLETE
            backup.snapshot_at = parse_datetime(payload["created_at"])
            backup.completed_at = timezone.now()
            backup.checksum = storage.checksum(token)
            backup.size = len(token)
            backup.row_counts = snapshots.row_counts(payload)
            backup.save()
            record_event("backup.success", actor=actor, backup=backup, new_value={"kind": kind})
        return backup
    except (BackupError, OSError, DatabaseError, ValueError) as error:
        message = (
            str(error)
            if isinstance(error, BackupError)
            else "Backup failed. Check server storage and database availability."
        )
        Backup.objects.filter(pk=backup.pk).update(
            status=Backup.Status.FAILED, error=message, completed_at=timezone.now()
        )
        record_event("backup.failure", actor=actor, backup=backup, new_value={"reason": message})
        raise BackupError(message) from None


@sensitive_variables()
def _create(*, actor, kind):
    try:
        storage.cipher()
        with transaction.atomic():
            snapshots.lock_tables()
            if actor is not None:
                actor = require_admin(actor)
            payload = snapshots.capture()
    except (BackupError, DatabaseError) as error:
        message = (
            str(error)
            if isinstance(error, BackupError)
            else "Backup could not read a consistent database snapshot. Please retry."
        )
        backup = Backup.objects.create(
            kind=kind,
            requested_by=actor.username if actor else "scheduler",
            status=Backup.Status.FAILED,
            error=message,
            completed_at=timezone.now(),
        )
        record_event("backup.failure", actor=actor, backup=backup, new_value={"reason": message})
        raise BackupError(message) from None
    return _store(payload, actor=actor, kind=kind)


def create_backup(*, actor):
    actor = require_admin(actor)
    with database_lock(OPERATION_LOCK):
        recover_interrupted()
        return _create(actor=actor, kind=Backup.Kind.MANUAL)


@sensitive_variables()
def import_backup(*, actor, token):
    actor = require_admin(actor)
    with database_lock(OPERATION_LOCK):
        recover_interrupted()
        try:
            payload = storage.decrypt(token)
            snapshots.validate(payload)
        except BackupError:
            record_event("backup.import_rejected", actor=actor)
            raise
        return _store(payload, actor=actor, kind=Backup.Kind.IMPORTED, token=token)


def download_backup(*, actor, backup):
    actor = require_admin(actor)
    if backup.status != Backup.Status.COMPLETE:
        raise BackupError("Only completed backups can be downloaded or restored.")
    token = storage.read(backup)
    record_event("backup.download", actor=actor, backup=backup)
    return token


@sensitive_variables()
def restore_backup(*, actor, backup, password):
    actor = require_admin(actor)
    authenticated = check_login(None, actor.username, password)
    if authenticated is None:
        record_event("restore.denied", actor=actor, backup=backup)
        raise ValidationError("Your password was not accepted, or your account is locked.")
    # Reauthentication occurs before the exclusive gate; check for account changes again under it.
    auth_hash = authenticated.get_session_auth_hash()
    with database_lock(MAINTENANCE_LOCK), database_lock(OPERATION_LOCK):
        recover_interrupted()
        actor = require_admin(actor)
        if not constant_time_compare(auth_hash, actor.get_session_auth_hash()):
            raise PermissionDenied("Your account changed. Log in again before restoring.")
        try:
            if backup.status != Backup.Status.COMPLETE:
                raise BackupError("Only completed backups can be restored.")
            token = storage.read(backup)
            payload = storage.decrypt(token)
            snapshots.validate(payload)
            # A failed safety backup aborts restore before any live records are replaced.
            safety = _create(actor=actor, kind=Backup.Kind.SAFETY)
            with transaction.atomic():
                snapshots.lock_tables(restore=True)
                actor = require_admin(actor)
                snapshots.replace(payload)
                record_event(
                    "restore.success",
                    actor=actor,
                    backup=backup,
                    new_value={"safety_backup": str(safety.pk), "snapshot_at": payload["created_at"]},
                )
            return safety
        except (BackupError, DatabaseError, ValueError) as error:
            message = (
                str(error)
                if isinstance(error, BackupError)
                else "Restore failed validation or could not finish. Current data is unchanged."
            )
            record_event("restore.failure", actor=actor, backup=backup, new_value={"reason": message})
            raise BackupError(message) from None


def next_daily(time, now=None):
    now = now or timezone.now()
    local = now.astimezone(IST)
    result = datetime.combine(local.date(), time.replace(tzinfo=None), tzinfo=IST)
    return result + timedelta(days=1) if result <= now else result


def configure_schedule(*, actor, enabled, time):
    actor = require_admin(actor)
    if enabled and time is None:
        raise ValidationError("Choose a daily backup time.")
    with database_lock(OPERATION_LOCK), transaction.atomic():
        schedule, _ = BackupSchedule.objects.select_for_update().get_or_create(pk=1)
        previous = {"enabled": schedule.enabled, "time": str(schedule.time)}
        schedule.enabled, schedule.time = enabled, time
        schedule.next_run_at = next_daily(time) if enabled else None
        schedule.updated_by = actor.username
        schedule.last_error = ""
        schedule.full_clean()
        schedule.save()
        record_event(
            "backup.schedule",
            actor=actor,
            old_value=previous,
            new_value={"enabled": enabled, "time": str(time), "timezone": "Asia/Kolkata"},
        )
        return schedule


def run_due_backup():
    """Call once a minute. PostgreSQL serializes multiple workers; missed runs catch up once."""
    with database_lock(OPERATION_LOCK):
        recover_interrupted()
        with transaction.atomic():
            schedule = BackupSchedule.objects.select_for_update().filter(pk=1, enabled=True).first()
            now = timezone.now()
            if not schedule or not schedule.next_run_at or schedule.next_run_at > now:
                return None
            # A crashed attempt is retried after 15 minutes; a completed attempt moves to tomorrow.
            schedule.last_attempt_at = now
            schedule.next_run_at = now + timedelta(minutes=15)
            schedule.save(update_fields=["last_attempt_at", "next_run_at"])
        try:
            backup = _create(actor=None, kind=Backup.Kind.SCHEDULED)
        except BackupError as error:
            BackupSchedule.objects.filter(pk=1).update(last_error=str(error))
            raise
        BackupSchedule.objects.filter(pk=1).update(
            last_success_at=timezone.now(),
            last_error="",
            next_run_at=next_daily(schedule.time),
        )
        return backup
