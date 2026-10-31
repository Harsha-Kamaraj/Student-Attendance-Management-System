"""Synthetic academic-year fixture for BL-29's guarded PostgreSQL database."""

import time
import uuid

from .performance import VerificationError, database_guard, environment_details, teaching_days_before, utc_now

PREFIX = "BL29"


def actual_counts():
    from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
    from apps.accounts.models import User
    from apps.attendance.models import AttendanceRecord, AttendanceSession
    from apps.notifications.models import Notification, ShortageFlag

    return {
        "students": Student.objects.count(),
        "faculty": Faculty.objects.count(),
        "users": User.objects.count(),
        "sections": Section.objects.count(),
        "subjects": Subject.objects.count(),
        "assignments": TeachingAssignment.objects.count(),
        "enrollments": Enrollment.objects.count(),
        "sessions": AttendanceSession.objects.count(),
        "attendance_records": AttendanceRecord.objects.count(),
        "notifications": Notification.objects.count(),
        "shortage_flags": ShortageFlag.objects.count(),
    }


def seed_database(plan):
    from django.conf import settings
    from django.db import connection, transaction
    from django.utils import timezone

    from apps.academics.models import Enrollment, Faculty, Section, Student, Subject, TeachingAssignment
    from apps.accounts.models import Role, User
    from apps.attendance.models import AttendanceRecord, AttendanceSession, AttendanceThreshold
    from apps.audit.models import AuditEntry
    from apps.notifications.models import Notification, ShortageFlag

    database = database_guard(settings.DATABASES["default"])
    for model in (
        User,
        Student,
        Faculty,
        Section,
        Subject,
        TeachingAssignment,
        Enrollment,
        AttendanceSession,
        AttendanceRecord,
        AuditEntry,
        Notification,
        ShortageFlag,
    ):
        if model.objects.exists():
            raise VerificationError(
                "Seed refuses a populated database. Migrate a fresh verification_bl29_* database."
            )
    started = time.perf_counter()
    today = timezone.localdate()
    calendar = teaching_days_before(today, plan["dataset"]["teaching_days"])
    print("BL-29 seed: creating synthetic identities, enrollments and 12,750 sessions", flush=True)
    with transaction.atomic():
        users = (
            [
                User(
                    username=f"{PREFIX}S{index:04}",
                    email=f"student{index:04}@attendance.invalid",
                    password="!BL29-fixture-not-a-login-password",
                    role=Role.STUDENT,
                    otp_confirmed=True,
                )
                for index in range(1000)
            ]
            + [
                User(
                    username=f"{PREFIX}F{index:03}",
                    email=f"faculty{index:03}@attendance.invalid",
                    password="!BL29-fixture-not-a-login-password",
                    role=Role.FACULTY,
                    otp_confirmed=True,
                )
                for index in range(60)
            ]
            + [
                User(
                    username=f"{PREFIX}ADMIN",
                    email="administrator@attendance.invalid",
                    password="!BL29-fixture-not-a-login-password",
                    role=Role.ADMIN,
                    otp_confirmed=True,
                )
            ]
        )
        User.objects.bulk_create(users, batch_size=500)
        users_by_name = {user.username: user for user in users}
        faculty = Faculty.objects.bulk_create(
            [
                Faculty(
                    user=users_by_name[f"{PREFIX}F{index:03}"],
                    faculty_id=f"{PREFIX}F{index:03}",
                    full_name=f"Synthetic faculty {index:03}",
                    department="Verification",
                )
                for index in range(60)
            ]
        )
        sections = Section.objects.bulk_create(
            [Section(class_name="BL29 synthetic cohort", name=f"Section{index:03}") for index in range(17)]
        )
        subjects = Subject.objects.bulk_create(
            [Subject(code=f"{PREFIX}SUB{index}", name=f"Synthetic subject {index}") for index in range(5)]
        )
        students = Student.objects.bulk_create(
            [
                Student(
                    user=users_by_name[f"{PREFIX}S{index:04}"],
                    roll_number=f"{PREFIX}S{index:04}",
                    full_name=f"Synthetic student {index:04}",
                    home_section=sections[index // 60],
                )
                for index in range(1000)
            ]
        )
        assignments = TeachingAssignment.objects.bulk_create(
            [
                TeachingAssignment(
                    section=section,
                    subject=subject,
                    faculty=faculty[
                        0 if section_index == 0 else 1 + ((section_index - 1) * 5 + subject_index) % 59
                    ],
                )
                for section_index, section in enumerate(sections)
                for subject_index, subject in enumerate(subjects)
            ]
        )
        Enrollment.objects.bulk_create(
            [
                Enrollment(
                    student=student, assignment=assignments[index // 60 * 5 + subject_index], subject=subject
                )
                for index, student in enumerate(students)
                for subject_index, subject in enumerate(subjects)
            ],
            batch_size=2000,
        )
        sessions = []
        for section_index in range(17):
            for occurrence in range(750):
                assignment = assignments[section_index * 5 + occurrence % 5]
                sessions.append(
                    AttendanceSession(
                        assignment=assignment,
                        date=calendar[occurrence // 3],
                        period=occurrence % 3 + 1,
                        recorded_by=assignment.faculty.user,
                        recorded_by_code=assignment.faculty.faculty_id,
                    )
                )
        AttendanceSession.objects.bulk_create(sessions, batch_size=2000)
        print("BL-29 seed: inserting 750,000 synthetic marks inside PostgreSQL", flush=True)
        # Fixture setup deliberately bypasses application notifications/audit.
        # Generate rows in the database instead of retaining 750k Python objects.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO attendance_attendancerecord (session_id, student_id, status)
                SELECT meeting.id, enrollment.student_id,
                       CASE WHEN meeting.ordinal <=
                           CASE WHEN right(student.roll_number, 4)::integer < 60 THEN 113
                                ELSE CASE mod(right(student.roll_number, 4)::integer, 4)
                                     WHEN 0 THEN 113 WHEN 1 THEN 112 WHEN 2 THEN 150 ELSE 0 END
                           END
                       THEN 'P' ELSE 'A' END
                FROM (
                    SELECT id, assignment_id,
                           row_number() OVER (PARTITION BY assignment_id ORDER BY date, period, id) AS ordinal
                    FROM attendance_attendancesession
                ) AS meeting
                JOIN academics_enrollment AS enrollment ON enrollment.assignment_id = meeting.assignment_id
                JOIN academics_student AS student ON student.id = enrollment.student_id
            """,
                [],
            )
        below = [student for index, student in enumerate(students) if index >= 60 and index % 4 in (1, 3)]
        ShortageFlag.objects.bulk_create(
            [
                ShortageFlag(student=student, subject=subject)
                for student in below
                for subject in [*subjects, None]
            ],
            batch_size=2000,
        )
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient=student.user,
                    title="Synthetic historical shortage",
                    body="Fictional verification fixture; no real student data or email was used.",
                )
                for student in below
            ],
            batch_size=1000,
        )
        AttendanceThreshold.objects.update_or_create(pk=1, defaults={"value": 75})
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE")
    counts = actual_counts()
    for key in (
        "students",
        "faculty",
        "sections",
        "subjects",
        "assignments",
        "sessions",
        "attendance_records",
    ):
        if counts[key] != plan["dataset"][key]:
            raise VerificationError(f"Seed count mismatch for {key}: {counts[key]}")
    return {
        "outcome": "seeded",
        "dataset_id": str(uuid.uuid4()),
        "database_name": database,
        "seed_plan_id": plan["plan_id"],
        "seeded_at": utc_now(),
        "plan_declared_at": plan["declared_at"],
        "source_revision": plan["source_revision"],
        "dataset": plan["dataset"],
        "actual_counts": counts,
        "seed_seconds": time.perf_counter() - started,
        "benchmark_day": today.isoformat(),
        "calendar": {
            "first": calendar[0].isoformat(),
            "last": calendar[-1].isoformat(),
            "teaching_days": len(calendar),
            "span_calendar_days": (calendar[-1] - calendar[0]).days + 1,
            "semester_start": calendar[-125].isoformat(),
            "semester_end": calendar[-1].isoformat(),
        },
        "fixture_notes": [
            "Exactly 750 saved classes per student across five subjects over 250 Mon–Sat teaching days.",
            "First 60 students have 113/150 per subject: first measured absence triggers a subject shortage.",
            "Other students vary between 113,112,150,0 present per 150; prior flags are synthetic.",
            "Fictional .invalid identities use unusable passwords; sessions are prepared later.",
            "No user data, credentials, tokens or services outside this verification database are changed.",
        ],
        "environment": environment_details(),
    }
