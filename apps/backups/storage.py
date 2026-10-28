"""Private, authenticated-encrypted files, published only after a complete durable write."""

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.views.decorators.debug import sensitive_variables

from .locks import BackupError


@sensitive_variables()
def cipher():
    try:
        return Fernet(settings.BACKUP_ENCRYPTION_KEY)
    except (TypeError, ValueError):
        raise BackupError(
            "Configure a valid backup encryption key on the server before using backups."
        ) from None


def directory():
    root = Path(settings.BACKUP_DIRECTORY).expanduser().absolute()
    if root.is_symlink():
        raise BackupError("The backup directory must be a private directory, not a symbolic link.")
    resolved = root.resolve()
    public = [Path(settings.BASE_DIR) / "static", Path(settings.BASE_DIR) / "staticfiles"]
    for name in ("STATIC_ROOT", "MEDIA_ROOT"):
        if value := getattr(settings, name, None):
            public.append(Path(value))
    if resolved in Path(settings.BASE_DIR).resolve().parents or resolved == Path(settings.BASE_DIR).resolve():
        raise BackupError("Configure a dedicated private backup directory.")
    if any(resolved.is_relative_to(path.resolve()) for path in public):
        raise BackupError("Backups cannot be stored in publicly served file directories.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not root.is_dir() or root.stat().st_mode & 0o077:
        raise BackupError("The backup directory must have private permissions (0700).")
    return root


def checksum(data):
    return hashlib.sha256(data).hexdigest()


@sensitive_variables()
def encrypt(payload):
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    token = cipher().encrypt(raw)
    if len(token) > settings.BACKUP_MAX_BYTES:
        raise BackupError("The encrypted backup exceeds the configured size limit.")
    return token


@sensitive_variables()
def decrypt(token):
    if not token or len(token) > settings.BACKUP_MAX_BYTES:
        raise BackupError("The backup is empty or exceeds the configured size limit.")
    try:
        return json.loads(cipher().decrypt(token))
    except (InvalidToken, ValueError, UnicodeDecodeError, RecursionError):
        raise BackupError(
            "Backup integrity check failed. The file is damaged or uses a different key."
        ) from None


@sensitive_variables()
def publish(backup, token):
    root = directory()
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=root)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(token)
            stream.flush()
            os.fsync(stream.fileno())
        # link() atomically publishes a complete file and refuses to overwrite a previous one.
        os.link(temporary, root / backup.filename)
        folder = os.open(root, os.O_RDONLY)
        try:
            os.fsync(folder)
        finally:
            os.close(folder)
    finally:
        os.unlink(temporary)


@sensitive_variables()
def read(backup):
    try:
        path = directory() / backup.filename
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_mode & 0o077
                or info.st_size > settings.BACKUP_MAX_BYTES
            ):
                raise BackupError("The backup file has unsafe permissions or exceeds the size limit.")
            token = stream.read(settings.BACKUP_MAX_BYTES + 1)
    except OSError:
        raise BackupError("The backup file is unavailable. Check the server backup storage.") from None
    if len(token) != backup.size or checksum(token) != backup.checksum:
        raise BackupError("Backup checksum verification failed. Current data has not been changed.")
    return token
