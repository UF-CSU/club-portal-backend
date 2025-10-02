import re

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404

from core.abstracts.models import ScopeType
from utils.permissions import get_permission

User = get_user_model()


class CustomBackend(ModelBackend):
    """Custom backend for managing permissions, etc."""

    def authenticate(self, request, username=None, **kwargs):
        # Email Regex from: https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/

        if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", username):
            username = get_object_or_404(User, email=username)

        return super().authenticate(request, username, **kwargs)

    def get_club_permissions(self, user_obj, clubs, obj=None):
        """Get list of permissions user has with a club."""

        perm_ids = set(
            user_obj.club_memberships.filter(club__in=clubs)
            .prefetch_related("roles", "roles__permissions")
            .values_list("roles__permissions__id", flat=True)
        )
        return Permission.objects.filter(id__in=perm_ids).distinct()

    def has_global_perm(self, user_obj, perm):
        """
        Check if a user has permission to create objects that are not scoped.

        This just uses the default permission checking capability from django,
        instead of the custom methods defined in this backend.
        """

        return super(ModelBackend, self).has_perm(user_obj, perm)

    def user_is_club_useragent(self, user):
        return user.is_useragent and user.useragent.apikey_type == "club"

    def has_scoped_perm(self, user_obj, perm, obj=None):
        """Check if user has scoped permissions for an object."""

        # Check if user has this permission at all for any club.
        # Need this because DRF checks perms without an object
        # before checking perms on a specific object.
        if obj is None and self.user_is_club_useragent(user_obj):
            key = user_obj.useragent.club_apikey
            return get_permission(perm) in key.permissions.all()

        elif obj is None:
            perm_ids = set(
                user_obj.club_memberships.all()
                .prefetch_related("roles", "roles__permissions")
                .values_list("roles__permissions__id", flat=True)
            )
            perms = Permission.objects.filter(id__in=perm_ids).distinct()

            if get_permission(perm) in perms:
                return True

        if getattr(obj, "scope", ScopeType.GLOBAL) == ScopeType.GLOBAL:
            return super(ModelBackend, self).has_perm(user_obj, perm, obj)

        if obj.scope == ScopeType.CLUB:
            assert hasattr(obj, "clubs"), (
                'Club scoped objects must have a "clubs" attribute that returns a queryset or ManyToManyRel.'
            )

            scoped_clubs = obj.clubs.all()

            if self.user_is_club_useragent(user_obj):
                key = user_obj.useragent.club_apikey

                # Auto return false if not correct club
                # if not key.club.id == obj.club.id:
                if not scoped_clubs.filter(id=key.club.id).exists():
                    return False

                # Otherwise, check if the permission is assigned to the key
                perm_obj = get_permission(perm, obj)
                return perm_obj in key.permissions.all()

            else:
                # # Short circuit if there's one club, and the user is an admin of that club
                # if scoped_clubs.count() == 1:
                #     club = scoped_clubs.first()
                #     membership = user_obj.club_memberships.filter(club__id=club.id)

                #     if membership.exists():
                #         membership = membership.first()
                #         if membership.is_admin:
                #             return True

                # Otherwise return perms for all clubs
                club_perms = self.get_club_permissions(user_obj, scoped_clubs, obj)
                perm_obj = get_permission(perm, obj)

                return perm_obj in club_perms

    def has_perm(self, user_obj, perm, obj=None):
        """Runs when checking any user's permissions."""

        if user_obj.is_superuser:
            return True

        # Don't pass in obj, ModelBackend will short circuit and
        # return empty set for user permissions, always returning false.
        has_user_perm = super(ModelBackend, self).has_perm(user_obj, perm)

        return has_user_perm or self.has_scoped_perm(user_obj, perm, obj)
