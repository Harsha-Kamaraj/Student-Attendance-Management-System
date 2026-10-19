"""Make the audit table append-only inside PostgreSQL (SEC-21, OBJ-04).

Any UPDATE, DELETE or TRUNCATE on audit_auditentry is rejected, even if
application code tries it directly.
"""

from django.db import migrations

FORWARD = """
CREATE FUNCTION audit_reject_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit entries are append-only (% rejected)', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_entry_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_auditentry
    FOR EACH ROW EXECUTE FUNCTION audit_reject_change();

CREATE TRIGGER audit_entry_no_truncate
    BEFORE TRUNCATE ON audit_auditentry
    FOR EACH STATEMENT EXECUTE FUNCTION audit_reject_change();
"""

REVERSE = """
DROP TRIGGER IF EXISTS audit_entry_no_truncate ON audit_auditentry;
DROP TRIGGER IF EXISTS audit_entry_no_update_delete ON audit_auditentry;
DROP FUNCTION IF EXISTS audit_reject_change();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FORWARD, REVERSE),
    ]
