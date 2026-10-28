from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import requires

from . import services, storage
from .forms import ImportForm, RestoreForm, ScheduleForm
from .locks import BackupError
from .models import Backup, BackupSchedule


@never_cache
@requires("backup.manage")
@require_GET
def backup_list(request):
    schedule = BackupSchedule.objects.filter(pk=1).first()
    configuration_error = ""
    try:
        storage.cipher()
    except BackupError as error:
        configuration_error = str(error)
    return render(
        request,
        "backups/list.html",
        {
            "page_obj": Paginator(Backup.objects.all(), 20).get_page(request.GET.get("page")),
            "schedule": schedule,
            "configuration_error": configuration_error,
        },
    )


@never_cache
@requires("backup.manage")
@require_POST
def backup_create(request):
    try:
        backup = services.create_backup(actor=request.user)
    except BackupError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Backup {backup.pk} completed and stored encrypted.")
    return redirect("backup_list")


@never_cache
@requires("backup.manage")
@require_GET
def backup_download(request, pk):
    backup = get_object_or_404(Backup, pk=pk)
    try:
        token = services.download_backup(actor=request.user, backup=backup)
    except BackupError as error:
        messages.error(request, str(error))
        return redirect("backup_list")
    response = HttpResponse(token, content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{backup.filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@never_cache
@requires("backup.manage")
@require_http_methods(["GET", "POST"])
@sensitive_post_parameters("password")
@sensitive_variables()
def backup_restore(request, pk):
    backup = get_object_or_404(Backup, pk=pk, status=Backup.Status.COMPLETE)
    form = RestoreForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            services.restore_backup(actor=request.user, backup=backup, password=form.cleaned_data["password"])
        except (BackupError, ValidationError) as error:
            form.add_error(
                None, " ".join(error.messages) if isinstance(error, ValidationError) else str(error)
            )
        else:
            logout(request)
            messages.success(
                request,
                "Restore completed. Sign in using an account from the backup "
                "and a fresh authenticator or email code.",
            )
            return redirect("login")
    return render(request, "backups/restore.html", {"backup": backup, "form": form})


@never_cache
@requires("backup.manage")
@require_http_methods(["GET", "POST"])
def backup_schedule(request):
    schedule = BackupSchedule.objects.filter(pk=1).first()
    form = ScheduleForm(
        request.POST if request.method == "POST" else None,
        initial={"enabled": schedule.enabled, "time": schedule.time} if schedule else {},
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.configure_schedule(actor=request.user, **form.cleaned_data)
        except (BackupError, ValidationError) as error:
            form.add_error(
                None, " ".join(error.messages) if isinstance(error, ValidationError) else str(error)
            )
        else:
            messages.success(request, "Backup schedule saved.")
            return redirect("backup_list")
    return render(request, "backups/schedule.html", {"form": form})


@never_cache
@requires("backup.manage")
@require_http_methods(["GET", "POST"])
@sensitive_variables()
def backup_import(request):
    form = ImportForm(request.POST if request.method == "POST" else None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.import_backup(actor=request.user, token=form.cleaned_data["backup_file"].read())
        except BackupError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, "Encrypted backup imported. Current application data has not changed.")
            return redirect("backup_list")
    return render(request, "backups/import.html", {"form": form})
