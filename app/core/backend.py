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

        # TODO: Optimize this query
        perm_ids = list(
            user_obj.club_memberships.filter(club=club).values_list(
                "roles__permissions__id", flat=True
            )
        )

        return set(Permission.objects.filter(id__in=perm_ids))

    def has_perm(self, user_obj, perm, obj=None):
        """Runs when checking any user's permissions."""
        # TODO: Optimize/cache this process, too many queries being made

        if user_obj.is_superuser:
            return True

        # Check if user has this permission at all for any club.
        # Need this because DRF checks perms without an object
        # before checking perms on a specific object.
        if obj is None:
            perm_ids = set(
                user_obj.club_memberships.all().values_list(
                    "roles__permissions__id", flat=True
                )
            )
            perms = Permission.objects.filter(id__in=perm_ids).distinct()

            if get_permission(perm) in perms:
                return True

        if getattr(obj, "scope", Scope.GLOBAL) == Scope.GLOBAL:
            return super().has_perm(user_obj, perm, obj)

        if obj.scope == Scope.CLUB:
            assert hasattr(
                obj, "club"
            ), 'Club scoped objects must have a "club" attribute.'

            if user_obj.is_useragent and user_obj.useragent.apikey_type == "club":
                key = user_obj.useragent.club_apikey

                # Auto return false if not correct club
                if not key.club.id == obj.club.id:
                    return False

                # Otherwise, check if the permission is assigned to the key
                perm = get_permission(perm, obj)
                return perm in key.permissions.all()

            else:
                club_perms = self.get_club_permissions(user_obj, obj.club, obj)
                perm = get_permission(perm, obj)

                return perm in club_perms

        return super().has_perm(user_obj, perm, obj)
