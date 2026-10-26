from django.db import migrations, models


def create_default_window(apps, schema_editor):
    apps.get_model("attendance", "CorrectionWindow").objects.using(schema_editor.connection.alias).get_or_create(
        pk=1, defaults={"days": 2}
    )


class Migration(migrations.Migration):
    dependencies = [("attendance", "0003_alter_attendancethreshold_value")]

    operations = [
        migrations.CreateModel(
            name="CorrectionWindow",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("days", models.PositiveSmallIntegerField(default=2)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(condition=models.Q(pk=1), name="correction_window_singleton"),
                    models.CheckConstraint(
                        condition=models.Q(days__gte=0, days__lte=30), name="correction_window_days_range"
                    ),
                ]
            },
        ),
        migrations.RunPython(create_default_window, migrations.RunPython.noop),
    ]
