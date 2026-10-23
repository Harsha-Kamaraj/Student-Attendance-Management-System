"""Load the fictional BL-28 test dataset described in Documents/Test_Data_Fixture.md.

Usage (development or a disposable test database only):

    python manage.py seed_test_data

Every account uses the password ``Attend#2026``. The command refuses to run when
DEBUG is off, and refuses to run twice, so it can never overwrite real data.
"""

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
from apps.accounts.models import Role, User
from apps.attendance.models import MAX_PERIODS_PER_DAY, AttendanceRecord, AttendanceSession, Status

PASSWORD = "Attend#2026"
CLASS_NAME = "B.Tech CSE Year 2"

ADMINS = ["ADMIN1"]
FACULTY = [  # faculty ID, name, department
    ("F001", "Dr. Test One", "CSE"),
    ("F002", "Dr. Test Two", "Mathematics"),
    ("F003", "Dr. Test Three", "CSE"),  # no classes
]
STUDENTS = [  # roll number, name, home section
    ("S001", "Test Student One", "A"),
    ("S002", "Test Student Two", "A"),
    ("S003", "Test Student Three", "B"),
    ("S004", "Test Student Four", "A"),
]

# CS101 in section A: 100 sessions; Present counts give the threshold boundaries.
CS101_SESSIONS = 100
CS101_START = datetime.date(2026, 6, 1)
CS101_PRESENT = {"S001": 74, "S002": 75, "S004": 76}

# MA101 in section B: S001's date-filter sessions (S003 joined later, so has no records).
MA101_SESSIONS = [
    (datetime.date(2026, 10, 1), Status.PRESENT),
    (datetime.date(2026, 10, 2), Status.ABSENT),
    (datetime.date(2026, 10, 3), Status.PRESENT),
]

FIXTURE_USERNAMES = ADMINS + [f[0] for f in FACULTY] + [s[0] for s in STUDENTS]


class Command(BaseCommand):
    help = "Load the fictional BL-28 test dataset (DEBUG only; refuses to run twice)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Refusing to load test data: DEBUG is off. Use a development database only.")
        existing = sorted(
            User.objects.filter(username__in=FIXTURE_USERNAMES).values_list("username", flat=True)
        )
        if existing:
            raise CommandError(
                f"Test data already loaded (found {', '.join(existing)}). Use a fresh database to reload it."
            )

        with transaction.atomic():
            self.create_data()

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded test data: {len(ADMINS)} admin, {len(FACULTY)} faculty, {len(STUDENTS)} students, "
                f"{CS101_SESSIONS + len(MA101_SESSIONS)} attendance sessions. Password for all: {PASSWORD}"
            )
        )

    def create_data(self):
        for username in ADMINS:
            User.objects.create_user(username=username, password=PASSWORD, role=Role.ADMIN)

        faculty = {}
        for code, name, department in FACULTY:
            user = User.objects.create_user(username=code, password=PASSWORD, role=Role.FACULTY)
            faculty[code] = Faculty.objects.create(
                user=user, faculty_id=code, full_name=name, department=department
            )

        sections = {name: Section.objects.create(class_name=CLASS_NAME, name=name) for name in ("A", "B")}
        cs101 = Subject.objects.create(code="CS101", name="Programming")
        ma101 = Subject.objects.create(code="MA101", name="Mathematics")
        cs101_a = TeachingAssignment.objects.create(
            section=sections["A"], subject=cs101, faculty=faculty["F001"]
        )
        ma101_b = TeachingAssignment.objects.create(
            section=sections["B"], subject=ma101, faculty=faculty["F002"]
        )

        students = {}
        for roll, name, home in STUDENTS:
            user = User.objects.create_user(username=roll, password=PASSWORD, role=Role.STUDENT)
            students[roll] = Student.objects.create(
                user=user, roll_number=roll, full_name=name, home_section=sections[home]
            )

        for roll in CS101_PRESENT:
            Enrollment.objects.create(student=students[roll], assignment=cs101_a)
        Enrollment.objects.create(student=students["S001"], assignment=ma101_b)

        for index in range(CS101_SESSIONS):
            day = CS101_START + datetime.timedelta(days=index // MAX_PERIODS_PER_DAY)
            session = AttendanceSession.objects.create(
                assignment=cs101_a,
                date=day,
                period=index % MAX_PERIODS_PER_DAY + 1,
                recorded_by=faculty["F001"].user,
                recorded_by_code="F001",
            )
            AttendanceRecord.objects.bulk_create(
                AttendanceRecord(
                    session=session,
                    student=students[roll],
                    status=Status.PRESENT if index < present else Status.ABSENT,
                )
                for roll, present in CS101_PRESENT.items()
            )

        for day, status in MA101_SESSIONS:
            session = AttendanceSession.objects.create(
                assignment=ma101_b,
                date=day,
                period=1,
                recorded_by=faculty["F002"].user,
                recorded_by_code="F002",
            )
            AttendanceRecord.objects.create(session=session, student=students["S001"], status=status)

        # S003 joined MA101 after its sessions were held, so S003 has no attendance records.
        Enrollment.objects.create(student=students["S003"], assignment=ma101_b)
