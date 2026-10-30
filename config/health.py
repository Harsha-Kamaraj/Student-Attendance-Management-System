"""Minimal database/maintenance readiness signal for availability measurements (BL-29)."""

from django.contrib.auth.decorators import login_not_required
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.backups.locks import MAINTENANCE_LOCK, BackupBusy, database_lock


@login_not_required
@never_cache
@require_GET
def health(request):
    try:
        with database_lock(MAINTENANCE_LOCK, shared=True), connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                return JsonResponse({"status": "unavailable"}, status=503)
    except (DatabaseError, BackupBusy):
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
