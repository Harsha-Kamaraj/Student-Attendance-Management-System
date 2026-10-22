from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendanceThreshold",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.PositiveSmallIntegerField(default=75, help_text="Whole-number percentage from 1 to 100.")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=models.Q(("value__gte", 1), ("value__lte", 100)), name="attendance_threshold_range"),
                ],
            },
        ),
    ]
