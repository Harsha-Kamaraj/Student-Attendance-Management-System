"""Monday 08:00 IST faculty shortage email (BL-24, BL-01 D-15).

Schedule with cron on the server, for example:

    CRON_TZ=Asia/Kolkata
    0 8 * * 1  cd /path/to/app && .venv/bin/python manage.py send_weekly_shortage_emails

Safe to re-run: each faculty member gets at most one email per week, and none when their
list is empty.
"""

from django.core.management.base import BaseCommand

from apps.notifications.services import send_weekly_faculty_emails


class Command(BaseCommand):
    help = "Email each faculty member the list of their students below the attendance threshold."

    def handle(self, *args, **options):
        result = send_weekly_faculty_emails()
        self.stdout.write(
            f"Sent {result['sent']}; empty lists skipped {result['empty']}; "
            f"already sent this week {result['already_sent']}; failed {result['failed']}."
        )
