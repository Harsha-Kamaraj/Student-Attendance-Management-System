from django.http import HttpResponse
from django.urls import Resolver404, resolve

from .locks import MAINTENANCE_LOCK, BackupBusy, database_lock


class RestoreMaintenanceMiddleware:
    """Drain active requests before restore and reject new ones until it commits.

    The gate wraps session/authentication middleware so an old authenticated request
    cannot resume a write after restore. Restore POST takes the exclusive gate in its service.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            restore = request.method == "POST" and resolve(request.path_info).url_name == "backup_restore"
        except Resolver404:
            restore = False
        if restore:
            return self.get_response(request)
        try:
            with database_lock(MAINTENANCE_LOCK, shared=True):
                return self.get_response(request)
        except BackupBusy:
            response = HttpResponse("Data recovery is in progress. Please try again shortly.", status=503)
            response["Retry-After"] = "30"
            response["Cache-Control"] = "no-store"
            return response
