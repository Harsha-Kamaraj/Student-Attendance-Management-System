"""Backup file safety on the actual host filesystem, without database fixtures."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import skipUnless

from django.test import SimpleTestCase, override_settings

from . import storage
from .locks import BackupError


class BackupStorageTests(SimpleTestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name) / "private-backups"
        configuration = override_settings(BACKUP_DIRECTORY=self.root)
        configuration.enable()
        self.addCleanup(configuration.disable)
        self.token = b"authenticated-encrypted-test-token"
        self.backup = SimpleNamespace(
            filename="sample.sambak", size=len(self.token), checksum=storage.checksum(self.token)
        )

    def test_private_publication_reads_back_and_refuses_to_replace_existing_backup(self):
        storage.publish(self.backup, self.token)
        self.assertEqual(storage.read(self.backup), self.token)
        with self.assertRaises(OSError):
            storage.publish(self.backup, b"must-not-overwrite")
        self.assertEqual(storage.read(self.backup), self.token)
        self.assertEqual(list(self.root.glob(".pending-*")), [])

    @skipUnless(os.name == "nt", "Windows access control is verified on Windows.")
    def test_windows_rejects_public_file_acl_using_the_opened_handle(self):
        storage.publish(self.backup, self.token)
        windows = storage._windows_storage()
        setter = windows.advapi.SetFileSecurityW
        setter.argtypes = [windows.wintypes.LPCWSTR, windows.wintypes.DWORD, windows.ctypes.c_void_p]
        setter.restype = windows.wintypes.BOOL
        with windows.descriptor(f"D:P(A;;FA;;;{windows.user_sid})(A;;FR;;;WD)") as descriptor:
            windows._check(setter(str(self.root / self.backup.filename), 0x80000004, descriptor))
        with self.assertRaisesMessage(BackupError, "unauthorized principal"):
            storage.read(self.backup)

    @skipUnless(os.name == "nt", "Windows access control is verified on Windows.")
    def test_windows_rejects_an_existing_public_directory_acl(self):
        storage.directory()
        windows = storage._windows_storage()
        setter = windows.advapi.SetFileSecurityW
        setter.argtypes = [windows.wintypes.LPCWSTR, windows.wintypes.DWORD, windows.ctypes.c_void_p]
        setter.restype = windows.wintypes.BOOL
        with windows.descriptor(f"D:P(A;OICI;FA;;;{windows.user_sid})(A;OICI;FR;;;WD)") as descriptor:
            windows._check(setter(str(self.root), 0x80000004, descriptor))
        with self.assertRaisesMessage(BackupError, "unauthorized principal"):
            storage.directory()

    @skipUnless(os.name == "nt", "Windows reparse-point handling is verified on Windows.")
    def test_windows_refuses_a_junction_in_a_backup_path(self):
        # Junctions need no symlink privilege: exercise the actual reparse-point
        # check even on Windows machines where symbolic-link creation is disabled.
        import ctypes
        import struct
        from ctypes import wintypes

        target = self.root.parent / "target"
        target.mkdir()
        junction = self.root.parent / "junction"
        junction.mkdir()
        windows = storage._windows_storage()
        handle = windows.kernel.CreateFileW(
            windows.native_path(junction), 0x40000000, 0, None, 3, 0x02200000, None
        )
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try:
            # An FSCTL_SET_REPARSE_POINT mount-point buffer (IO_REPARSE_TAG_MOUNT_POINT).
            substitute = ("\\??\\" + str(target)).encode("utf-16-le")
            print_name = str(target).encode("utf-16-le")
            names = substitute + b"\0\0" + print_name + b"\0\0"
            data = struct.pack("<HHHH", 0, len(substitute), len(substitute) + 2, len(print_name)) + names
            buffer = struct.pack("<IHH", 0xA0000003, len(data), 0) + data
            control = windows.kernel.DeviceIoControl
            control.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.c_void_p,
                ctypes.c_void_p,
            ]
            control.restype = wintypes.BOOL
            returned = wintypes.DWORD()
            native_buffer = ctypes.create_string_buffer(buffer)
            windows._check(
                control(handle, 0x000900A4, native_buffer, len(buffer), None, 0, ctypes.byref(returned), None)
            )
        finally:
            windows.kernel.CloseHandle(handle)
        with override_settings(BACKUP_DIRECTORY=junction / "backups"):
            with self.assertRaisesMessage(BackupError, "reparse points"):
                storage.directory()
        # Remove the junction itself; never traverse or delete the target.
        junction.rmdir()
