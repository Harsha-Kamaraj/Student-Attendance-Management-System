"""Ending a user's stored login sessions (D-03, D-04, SEC-15).

Sessions live in the database (`django_session`). Logout deletes the current row; this helper
deletes every row that belongs to one user, so a deactivated or deleted account leaves no usable
or leftover session behind on any device. Expired rows of other users are removed by Django's
`clearsessions` command, which the server scheduler runs daily (README, "Scheduled jobs").
"""

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session


def end_user_sessions(user_id):
    """Delete every stored session that is signed in as `user_id`; return how many were removed."""
    owner = str(user_id)
    keys = [
        session.session_key
        for session in Session.objects.only("session_key", "session_data").iterator()
        if session.get_decoded().get(SESSION_KEY) == owner
    ]
    if keys:
        Session.objects.filter(session_key__in=keys).delete()
    return len(keys)
