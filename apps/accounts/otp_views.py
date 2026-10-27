"""Two-factor login pages (BL-33): setup, code entry, emailed codes and Admin reset."""

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_POST

from . import otp
from .forms import OTPCodeForm, ReauthenticateForm
from .models import User
from .permissions import requires

LOCKED_MESSAGE = "Too many wrong codes. Your account is locked for 15 minutes."


def _finish_login(request):
    request.session.cycle_key()  # new session ID once fully authenticated
    request.session[otp.SESSION_VERIFIED] = True


def _locked_out(request):
    logout(request)
    messages.error(request, LOCKED_MESSAGE)
    return redirect("login")


@never_cache
@login_required
@sensitive_post_parameters("code")
@sensitive_variables("secret", "codes", "context")
def otp_setup(request):
    user = request.user
    if otp.is_locked(user):
        return _locked_out(request)
    if user.otp_confirmed:
        return redirect("otp_verify")
    secret = request.session.get(otp.SESSION_SETUP_SECRET) or otp.new_secret()
    request.session[otp.SESSION_SETUP_SECRET] = secret
    form = OTPCodeForm(request.POST or None)
    form.fields["code"].help_text = "The 6-digit code your authenticator app shows after scanning."
    if request.method == "POST" and form.is_valid():
        try:
            codes = otp.confirm_setup(user, secret, form.cleaned_data["code"])
        except otp.AccountLocked:
            return _locked_out(request)
        except otp.AlreadyConfigured:
            request.session.pop(otp.SESSION_SETUP_SECRET, None)
            return redirect("otp_verify")
        if codes:
            del request.session[otp.SESSION_SETUP_SECRET]
            _finish_login(request)
            return render(request, "accounts/otp_backup_codes.html", {"codes": codes})
        user.refresh_from_db()
        if otp.is_locked(user):
            return _locked_out(request)
        form.add_error(
            "code", "That code is not right. Check the time on your phone and try the newest code."
        )
    context = {
        "form": form,
        "qr_svg": mark_safe(
            otp.qr_code_svg(otp.provisioning_uri(user, secret))
        ),  # generated SVG, no user input
        "manual_key": " ".join(secret[i : i + 4] for i in range(0, len(secret), 4)),
    }
    return render(request, "accounts/otp_setup.html", context)


@never_cache
@login_required
@sensitive_post_parameters("code")
def otp_verify(request):
    user = request.user
    if not user.otp_confirmed:
        return redirect("otp_setup")
    if request.session.get(otp.SESSION_VERIFIED):
        return redirect("dashboard")
    if otp.is_locked(user):
        return _locked_out(request)
    form = OTPCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ok, locked = otp.verify_code(user, form.cleaned_data["code"])
        if ok:
            _finish_login(request)
            return redirect("dashboard")
        if locked:
            return _locked_out(request)
        form.add_error("code", "That code is not right or has already been used.")
    return render(
        request,
        "accounts/otp_verify.html",
        {"form": form, "backup_left": otp.remaining_backup_codes(user), "has_email": bool(user.email)},
    )


@never_cache
@login_required
@require_POST
def otp_email(request):
    if not request.user.otp_confirmed:
        return redirect("otp_setup")
    if request.session.get(otp.SESSION_VERIFIED):
        return redirect("otp_verify")
    try:
        address = otp.send_email_code(request.user)
    except otp.NoEmailAddress:
        messages.error(request, "Your account has no email address. Use a backup code or contact the Admin.")
    except otp.TooManyEmailCodes:
        messages.error(
            request, "You can request at most 3 email codes in 15 minutes. Please wait and try again."
        )
    except otp.AccountLocked:
        return _locked_out(request)
    except otp.EmailDeliveryFailed:
        messages.error(request, "Email could not be sent. Use your authenticator app or a backup code.")
    else:
        messages.success(request, f"A code was sent to {address}. It is valid for 10 minutes.")
    return redirect("otp_verify")


@never_cache
@requires("accounts.manage")
@sensitive_post_parameters("password")
def account_reset_otp(request, pk):
    """Admin reset of another user's two-factor login, after re-entering their password (SEC-31)."""
    account = get_object_or_404(User, pk=pk)
    if account == request.user:
        raise PermissionDenied("Admins cannot reset their own OTP here.")
    form = ReauthenticateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        otp.reset_otp(user=account, reset_by=request.user)
        messages.success(
            request, f"OTP reset for {account.username}. They will set it up again at next login."
        )
        return redirect("account_list")
    return render(request, "accounts/otp_reset_confirm.html", {"account": account, "form": form})
