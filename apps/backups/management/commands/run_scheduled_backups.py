from django.core.management.base import BaseCommand, CommandError

from apps.backups.locks import BackupBusy, BackupError
from apps.backups.services import run_due_backup


class Command(BaseCommand):
    help = "Run one due backup. Invoke every minute from the server's task scheduler."

    def handle(self, *args, **options):
        try:
            backup = run_due_backup()
        except BackupBusy:
            self.stdout.write("Another operation is active; the schedule will be checked on the next tick.")
            return
        except BackupError as error:
            raise CommandError(str(error)) from None
        self.stdout.write(f"Backup {backup.pk} completed." if backup else "No backup is due.")
