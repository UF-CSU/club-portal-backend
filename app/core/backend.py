import re

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404

from core.abstracts.models import Scope
from utils.permissions import get_permission

User = get_user_model()


class CustomBackend(ModelBackend):
    """Custom backend for managing permissions, etc."""

    def authenticate(self, request, username=None, **kwargs):
        # Email Regex from: https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/

        if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", username):
            username = get_object_or_404(User, email=username)

        return super().authenticate(request, username, **kwargs)

    def get_club_permissions(self, user_obj, club, obj=None):
        """Get list of permissions user has with a club."""

        perm_ids = list(
            user_obj.club_memberships.filter(club=club).values_list(
                "roles__permissions__id", flat=True
            )
        )

        return set(Permission.objects.filter(id__in=perm_ids))

    def has_perm(self, user_obj, perm, obj=None):
        """Runs when checking any user's permissions."""
        # from clubs.models import Club

        if user_obj.is_superuser:
            return True

        if not hasattr(obj, "scope"):
            return super().has_perm(user_obj, perm, obj)

        if obj.scope == Scope.CLUB:
            assert hasattr(
                obj, "club"
            ), 'Club scoped objects must have a "club" attribute.'

            club_perms = self.get_club_permissions(user_obj, obj.club, obj)
            perm = get_permission(perm, obj)

            return perm in club_perms

        return super().has_perm(user_obj, perm, obj)
