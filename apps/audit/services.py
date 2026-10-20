from .models import AuditEntry


def record(
    action,
    *,
    actor=None,
    actor_username="",
    target_type="",
    target_id="",
    old_value=None,
    new_value=None,
    reason="",
    is_admin_override=False,
):
    """Append one audit entry. Never pass passwords or tokens (SEC-22)."""
    return AuditEntry.objects.create(
        actor_user_id=actor.pk if actor else None,
        actor_username=actor.username if actor else actor_username,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        is_admin_override=is_admin_override,
    )
