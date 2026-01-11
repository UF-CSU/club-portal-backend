from django.http import Http404
from rest_framework import permissions
from users.models import User

from polls.models import Poll


class CanViewSubmitPublicPoll(permissions.AllowAny):
    """Allow anyone to view and submit public polls."""

    pass


class CanViewPrivatePoll(CanViewSubmitPublicPoll):
    """Only members of a club can view that clubs polls."""

    def has_permission(self, request, view):
        return not request.user.is_anonymous and request.user.clubs.exists()


class CanSubmitPrivatePoll(CanViewPrivatePoll):
    pass


class CanAccessClubPoll(permissions.AllowAny):
    """Only allow members of a club to submit private polls for that club."""

    def has_permission(self, request, view):
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj: Poll):
        user: User = request.user

        if not obj.is_private:
            return super().has_object_permission(request, view, obj)
        elif user.is_anonymous:
            raise Http404
        elif not user.clubs.filter(id=obj.club_id).exists():
            raise Http404

        # Return as-is if not required roles
        if not obj.allowed_club_roles.exists():
            return super().has_object_permission(request, view, obj)

        # Verify user has required role
        required_role_ids = obj.allowed_club_roles.values_list("id", flat=True)
        # return ClubRole.objects.filter(club__id=obj.club_id)
        has_perm = (
            user.club_memberships.get(club__id=obj.club_id)
            .roles.filter(id__in=required_role_ids)
            .exists()
        )

        if not has_perm and not user.has_perm("polls.view_private_poll"):
            raise Http404
        elif not has_perm:
            return False
        else:
            return True

        # return super().has_object_permission(request, view, obj)
