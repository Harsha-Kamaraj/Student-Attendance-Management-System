from django.shortcuts import render

from apps.audit import services as audit


def permission_denied(request, exception=None):
    """Every refused request: log it (SEC-12, SEC-22) and show no protected data."""
    user = request.user if request.user.is_authenticated else None
    audit.record(
        "access.denied",
        actor=user,
        target_type="path",
        target_id=f"{request.method} {request.path}"[:50],
        reason=str(exception or "")[:200],
    )
    return render(request, "403.html", status=403)
