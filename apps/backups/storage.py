"""Private, authenticated-encrypted files, published only after a complete durable write."""

import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.views.decorators.debug import sensitive_variables

from .locks import BackupError


class _WindowsStorage:
    """Use Windows ACLs and verified handles; POSIX mode bits do not describe NTFS access."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        self.ctypes, self.wintypes = ctypes, wintypes
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        pointer = ctypes.c_void_p

        def api(library, name, arguments, result=wintypes.BOOL):
            function = getattr(library, name)
            function.argtypes, function.restype = arguments, result
            return function

        api(self.kernel, "GetCurrentProcess", [], wintypes.HANDLE)
        api(self.kernel, "CloseHandle", [wintypes.HANDLE])
        api(self.kernel, "LocalFree", [pointer], pointer)
        api(self.kernel, "CreateDirectoryW", [wintypes.LPCWSTR, pointer])
        api(
            self.kernel,
            "CreateFileW",
            [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                pointer,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            ],
            wintypes.HANDLE,
        )
        api(
            self.kernel,
            "GetFileInformationByHandleEx",
            [wintypes.HANDLE, ctypes.c_int, pointer, wintypes.DWORD],
        )
        api(self.kernel, "MoveFileExW", [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD])
        api(self.advapi, "OpenProcessToken", [wintypes.HANDLE, wintypes.DWORD, pointer])
        api(
            self.advapi,
            "GetTokenInformation",
            [wintypes.HANDLE, ctypes.c_int, pointer, wintypes.DWORD, pointer],
        )
        api(self.advapi, "ConvertSidToStringSidW", [pointer, pointer])
        api(
            self.advapi,
            "ConvertStringSecurityDescriptorToSecurityDescriptorW",
            [wintypes.LPCWSTR, wintypes.DWORD, pointer, pointer],
        )
        api(
            self.advapi,
            "GetSecurityInfo",
            [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD, pointer, pointer, pointer, pointer, pointer],
            wintypes.DWORD,
        )
        api(self.advapi, "GetSecurityDescriptorControl", [pointer, pointer, pointer])
        api(self.advapi, "GetAce", [pointer, wintypes.DWORD, pointer])
        self.user_sid = self._current_user_sid()
        self.trusted_sids = {self.user_sid, "S-1-5-18", "S-1-5-32-544"}

    @staticmethod
    def native_path(path):
        name = str(Path(path).absolute())
        if name.startswith("\\\\?\\"):
            return name
        return "\\\\?\\UNC\\" + name[2:] if name.startswith("\\\\") else "\\\\?\\" + name

    def _check(self, success):
        if not success:
            raise self.ctypes.WinError(self.ctypes.get_last_error())

    def _sid_text(self, sid):
        text = self.wintypes.LPWSTR()
        self._check(self.advapi.ConvertSidToStringSidW(sid, self.ctypes.byref(text)))
        try:
            return text.value
        finally:
            self.kernel.LocalFree(self.ctypes.cast(text, self.ctypes.c_void_p))

    def _current_user_sid(self):
        token = self.wintypes.HANDLE()
        self._check(
            self.advapi.OpenProcessToken(self.kernel.GetCurrentProcess(), 8, self.ctypes.byref(token))
        )
        try:
            size = self.wintypes.DWORD()
            self.advapi.GetTokenInformation(token, 1, None, 0, self.ctypes.byref(size))
            data = self.ctypes.create_string_buffer(size.value)
            self._check(self.advapi.GetTokenInformation(token, 1, data, size, self.ctypes.byref(size)))
            return self._sid_text(self.ctypes.c_void_p.from_buffer(data).value)
        finally:
            self.kernel.CloseHandle(token)

    @contextmanager
    def descriptor(self, sddl):
        descriptor = self.ctypes.c_void_p()
        self._check(
            self.advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl,
                1,
                self.ctypes.byref(descriptor),
                None,
            )
        )
        try:
            yield descriptor
        finally:
            self.kernel.LocalFree(descriptor)

    def create_directory(self, path):
        class Attributes(self.ctypes.Structure):
            _fields_ = [
                ("length", self.wintypes.DWORD),
                ("descriptor", self.ctypes.c_void_p),
                ("inherit", self.wintypes.BOOL),
            ]

        path.parent.mkdir(parents=True, exist_ok=True)
        # Protect the leaf from inherited public permissions, granting only the
        # service account and the two privileged local Windows principals.
        sddl = f"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;{self.user_sid})"
        with self.descriptor(sddl) as descriptor:
            attributes = Attributes(self.ctypes.sizeof(Attributes), descriptor, False)
            if not self.kernel.CreateDirectoryW(self.native_path(path), self.ctypes.byref(attributes)):
                error = self.ctypes.get_last_error()
                if error != 183:  # ERROR_ALREADY_EXISTS: validate its actual ACL below.
                    raise self.ctypes.WinError(error)

    def _open(self, path, *, directory=False):
        # OPEN_REPARSE_POINT opens the link itself. Inspect the handle before
        # reading bytes; a name check followed by normal open would race a link swap.
        access = 0x20000 | (0x80 if directory else 0x80000000)  # READ_CONTROL + attributes/read
        share = 7 if directory else 1  # readers only while a backup file is open
        flags = 0x00200000 | (0x02000000 if directory else 0)  # no-follow, backup semantics
        handle = self.kernel.CreateFileW(self.native_path(path), access, share, None, 3, flags, None)
        if handle == self.ctypes.c_void_p(-1).value:
            raise self.ctypes.WinError(self.ctypes.get_last_error())
        return handle

    def _validate(self, handle, *, directory=False):
        class Attributes(self.ctypes.Structure):
            _fields_ = [("attributes", self.wintypes.DWORD), ("tag", self.wintypes.DWORD)]

        attributes = Attributes()
        self._check(
            self.kernel.GetFileInformationByHandleEx(
                handle,
                9,
                self.ctypes.byref(attributes),
                self.ctypes.sizeof(attributes),
            )
        )
        if attributes.attributes & 0x400 or bool(attributes.attributes & 0x10) != directory:
            raise BackupError(
                "Backup storage must use ordinary private directories and files, not reparse points."
            )
        owner, dacl, descriptor = (self.ctypes.c_void_p() for _ in range(3))
        error = self.advapi.GetSecurityInfo(
            handle,
            1,
            5,
            self.ctypes.byref(owner),
            None,
            self.ctypes.byref(dacl),
            None,
            self.ctypes.byref(descriptor),
        )
        if error:
            raise self.ctypes.WinError(error)
        try:
            if not owner.value or self._sid_text(owner) not in self.trusted_sids or not dacl.value:
                raise BackupError("Backup storage must have a private Windows owner and access-control list.")
            control, revision = self.wintypes.WORD(), self.wintypes.DWORD()
            self._check(
                self.advapi.GetSecurityDescriptorControl(
                    descriptor,
                    self.ctypes.byref(control),
                    self.ctypes.byref(revision),
                )
            )
            if directory and not control.value & 0x1000:  # SE_DACL_PROTECTED
                raise BackupError("The Windows backup directory must have protected private permissions.")
            # ACL header: revision byte, reserved byte, size WORD, ACE count WORD.
            count = self.wintypes.WORD.from_address(dacl.value + 4).value
            for index in range(count):
                ace = self.ctypes.c_void_p()
                self._check(self.advapi.GetAce(dacl, index, self.ctypes.byref(ace)))
                ace_type = self.ctypes.c_ubyte.from_address(ace.value).value
                if ace_type == 1:  # An access-denied ACE grants no access.
                    continue
                if ace_type != 0 or self._sid_text(ace.value + 8) not in self.trusted_sids:
                    raise BackupError("Backup storage grants Windows access to an unauthorized principal.")
        finally:
            self.kernel.LocalFree(descriptor)

    def validate_directory(self, path):
        handle = self._open(path, directory=True)
        try:
            self._validate(handle, directory=True)
        finally:
            self.kernel.CloseHandle(handle)

    def open_read(self, path):
        import msvcrt

        handle = self._open(path)
        try:
            self._validate(handle)
            # The CRT descriptor now owns the verified handle, including its
            # no-write/no-delete sharing policy for the entire read.
            return msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        except BaseException:
            self.kernel.CloseHandle(handle)
            raise

    def publish(self, temporary, destination):
        # Same directory/volume, no REPLACE_EXISTING: an existing backup is never overwritten.
        self._check(self.kernel.MoveFileExW(self.native_path(temporary), self.native_path(destination), 8))


@lru_cache(maxsize=1)
def _windows_storage():
    return _WindowsStorage()


def _reject_reparse_components(path):
    if os.name == "nt":
        for component in (path, *path.parents):
            try:
                attributes = component.lstat().st_file_attributes
            except FileNotFoundError:
                continue
            if attributes & 0x400:
                raise BackupError("Backup storage cannot contain symbolic links or Windows reparse points.")


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
    _reject_reparse_components(root)
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
    if os.name == "nt":
        try:
            windows = _windows_storage()
            windows.create_directory(root)
            windows.validate_directory(root)
        except OSError:
            raise BackupError(
                "The private Windows backup directory could not be opened or created."
            ) from None
    else:
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
        if os.name == "nt":
            # Validate inherited file permissions before publishing the complete file.
            os.close(_windows_storage().open_read(temporary))
            _windows_storage().publish(temporary, root / backup.filename)
        else:
            # link() atomically publishes a complete file and refuses to overwrite a previous one.
            os.link(temporary, root / backup.filename)
            folder = os.open(root, os.O_RDONLY)
            try:
                os.fsync(folder)
            finally:
                os.close(folder)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass  # Windows renamed the temporary file into its final name.


@sensitive_variables()
def read(backup):
    try:
        path = directory() / backup.filename
        fd = (
            _windows_storage().open_read(path)
            if os.name == "nt"
            else os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        )
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or (os.name != "nt" and info.st_mode & 0o077)
                or info.st_size > settings.BACKUP_MAX_BYTES
            ):
                raise BackupError("The backup file has unsafe permissions or exceeds the size limit.")
            token = stream.read(settings.BACKUP_MAX_BYTES + 1)
    except OSError:
        raise BackupError("The backup file is unavailable. Check the server backup storage.") from None
    if len(token) != backup.size or checksum(token) != backup.checksum:
        raise BackupError("Backup checksum verification failed. Current data has not been changed.")
    return token
