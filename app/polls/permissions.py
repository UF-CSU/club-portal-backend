from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, permissions
from users.models import User

from polls.models import Poll


class CanViewPoll(permissions.AllowAny):
    """Determine which users can view which polls."""

    def _has_required_club_role(self, user: User, poll: Poll):
        """Returns true if user has club role required to access poll."""

        required_role_ids = poll.allowed_club_roles.values_list("id", flat=True)
        membership = get_object_or_404(user.club_memberships, club__id=poll.club_id)

        if len(required_role_ids) == 0:
            return True

        return membership.roles.filter(id__in=required_role_ids).exists()

    def has_object_permission(self, request, view, obj):
        user: User = request.user

        if not obj.is_private:
            # Form is public, allow anyone
            return super().has_object_permission(request, view, obj)
        elif user.is_anonymous:
            # Unauthenticated user accessing private poll, raise 404
            raise Http404
        elif not user.clubs.filter(id=obj.club_id).exists():
            # Non-club member accessing private poll, raise 404
            raise Http404

        # Return as-is if private poll doesn't have required roles,
        # since this user is a member of the club
        if not obj.allowed_club_roles.all().exists():
            return super().has_object_permission(request, view, obj)

        # Users can only proceed if they have specific role,
        # or they have explicit permissions for viewing private polls
        has_role = self._has_required_club_role(user, obj)
        has_perm = user.has_perm("polls.view_private_poll", obj)
        if has_role or has_perm:
            return True
        else:
            raise Http404


class CanSubmitPoll(CanViewPoll):
    """Determine which users can submit which polls."""

    def has_object_permission(self, request, view, obj):
        if not obj.is_private:
            return True

        has_club_role = self._has_required_club_role(request.user, obj)
        has_view_perm = super().has_object_permission(request, view, obj)

        if has_view_perm and not has_club_role:
            # Return bad request since the user can view the form but cannot submit,
            # which would happen if club admin tries to submit a form with required role of "member"
            raise exceptions.ParseError()
        elif not has_view_perm:
            raise Http404
        else:
            return has_club_role and has_view_perm
