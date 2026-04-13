"""
General constants and initial values for club items.
"""

from typing import TypedDict

from core.abstracts.models import RoleType


class ClubRolePayloadType(TypedDict):
    name: str
    role_type: RoleType
    is_default: bool
    is_executive: bool
    is_official: bool
    is_voter: bool


class TeamRolePayloadType(TypedDict):
    name: str
    role_type: RoleType
    is_default: bool


CLUB_FOLLOWER_ROLE_PERMISSIONS = []
"""View public club info."""

CLUB_VIEWER_ROLE_PERMISSIONS = [
    *CLUB_FOLLOWER_ROLE_PERMISSIONS,
    # Clubs
    "clubs.view_club",
    "clubs.view_club_details",
    "clubs.view_team",
    "clubs.view_clubfile",
    "clubs.view_clubmembership",
    "clubs.view_clubrole",
    "clubs.view_clubphoto",
    "clubs.view_clubtag",
    "clubs.view_teammembership",
    "clubs.view_teamrole",
    # Events
    "events.view_event",
    "events.view_private_event",
    "events.view_event_details",
]
"""View internal club info & stats."""

CLUB_EDITOR_ROLE_PERMISSIONS = [
    *CLUB_VIEWER_ROLE_PERMISSIONS,
    # Clubs
    "clubs.change_club",
    "clubs.add_team",
    "clubs.change_team",
    "clubs.add_clubfile",
    "clubs.change_clubfile",
    "clubs.add_clubmembership",
    "clubs.change_clubmembership",
    "clubs.add_clubrole",
    "clubs.change_clubrole",
    "clubs.add_teammembership",
    "clubs.change_teammembership",
    "clubs.add_teamrole",
    "clubs.change_teamrole",
    # Events
    "events.add_event",
    "events.change_event",
    "events.view_recurringevent",
    "events.view_event_analytics",
    # Polls
    "polls.add_poll",
    "polls.change_poll",
    "polls.view_pollfield",
    "polls.add_pollfield",
    "polls.change_pollfield",
    "polls.delete_pollfield",
    "polls.view_choiceinputoption",
    "polls.view_pollsubmission",
    "polls.add_choiceinputoption",
    "polls.change_choiceinputoption",
    "polls.delete_choiceinputoption",
    "polls.view_poll_analytics",
    # Analytics
    "analytics.view_link",
    "analytics.add_link",
    "analytics.change_link",
    "analytics.delete_link",
    "analytics.view_qrcode",
    "analytics.add_qrcode",
    "analytics.change_qrcode",
    "analytics.delete_qrcode",
]
"""Edit and add permissions with some restrictions."""

CLUB_ADMIN_ROLE_PERMISSIONS = [
    *CLUB_EDITOR_ROLE_PERMISSIONS,
    # Clubs
    "clubs.delete_team",
    "clubs.delete_clubfile",
    "clubs.delete_clubmembership",
    "clubs.delete_clubrole",
    "clubs.delete_teammembership",
    "clubs.delete_teamrole",
    "clubs.add_clubapikey",
    "clubs.view_clubapikey",
    "clubs.change_clubapikey",
    "clubs.delete_clubapikey",
    # Events
    "events.delete_event",
    "events.add_recurringevent",
    "events.change_recurringevent",
    "events.delete_recurringevent",
    # Polls
    "polls.delete_poll",
    "polls.view_private_poll",
]
"""All permissions for a club"""

# TODO: Flesh out team permissions
TEAM_FOLLOWER_ROLE_PERMISSIONS = []
"""View public team info."""

TEAM_VIEWER_ROLE_PERMISSIONS = [
    *TEAM_FOLLOWER_ROLE_PERMISSIONS,
    # Teams
    "clubs.view_teammembership",
    "clubs.view_teamrole",
]
"""View internal team info & stats."""

TEAM_EDITOR_ROLE_PERMISSIONS = [
    *TEAM_VIEWER_ROLE_PERMISSIONS,
    # Teams
    "clubs.add_teammembership",
    "clubs.change_teammembership",
    "clubs.add_teamrole",
    "clubs.change_teamrole",
]
"""Edit and add permissions with some restrictions."""

TEAM_ADMIN_ROLE_PERMISSIONS = [
    *TEAM_EDITOR_ROLE_PERMISSIONS,
    # Teams
    "clubs.delete_teammembership",
    "clubs.delete_teamrole",
]
"""All permissions for a team"""

# Sort permissions lists to use for testing, assertions, etc
CLUB_VIEWER_ROLE_PERMISSIONS.sort()
CLUB_EDITOR_ROLE_PERMISSIONS.sort()
CLUB_ADMIN_ROLE_PERMISSIONS.sort()
TEAM_VIEWER_ROLE_PERMISSIONS.sort()
TEAM_EDITOR_ROLE_PERMISSIONS.sort()
TEAM_ADMIN_ROLE_PERMISSIONS.sort()


INITIAL_CLUB_ROLES: list[ClubRolePayloadType] = [
    {
        "name": "President",
        "role_type": RoleType.ADMIN,
        "is_default": False,
        "is_executive": True,
        "is_official": True,
        "is_voter": True,
    },
    {
        "name": "Vice-President",
        "role_type": RoleType.ADMIN,
        "is_default": False,
        "is_executive": True,
        "is_official": True,
        "is_voter": True,
    },
    {
        "name": "Officer",
        "role_type": RoleType.EDITOR,
        "is_default": False,
        "is_executive": False,
        "is_official": True,
        "is_voter": True,
    },
    {
        "name": "Member",
        "role_type": RoleType.VIEWER,
        "is_default": True,
        "is_executive": False,
        "is_official": True,
        "is_voter": False,
    },
    {
        "name": "Follower",
        "role_type": RoleType.FOLLOWER,
        "is_default": False,
        "is_executive": False,
        "is_official": False,
        "is_voter": False,
    },
]

INITIAL_TEAM_ROLES: list[TeamRolePayloadType] = [
    {
        "name": "Member",
        "role_type": RoleType.VIEWER,
        "is_default": True,
    },
    {"name": "Admin", "role_type": RoleType.ADMIN, "is_default": False},
]
