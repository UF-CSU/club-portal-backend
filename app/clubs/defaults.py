"""
General constants and initial values for club items.
"""

from typing import TypedDict

from clubs.models import RoleType


class RolePayloadType(TypedDict):
    name: str
    default: bool
    role_type: RoleType


FOLLOWER_ROLE_PERMISSIONS = []
"""View public club info."""

VIEWER_ROLE_PERMISSIONS = [
    *FOLLOWER_ROLE_PERMISSIONS,
    # Clubs
    "clubs.view_club",
    "clubs.view_club_details",
    "clubs.view_team",
    "clubs.view_clubfile",
    "clubs.view_clubmembership",
    "clubs.view_clubrole",
    "clubs.view_clubphoto",
    "clubs.view_clubtag",
    # Events
    "events.view_event",
    "events.view_private_event",
]
"""View internal club info & stats."""

EDITOR_ROLE_PERMISSIONS = [
    *VIEWER_ROLE_PERMISSIONS,
    # Clubs
    "clubs.change_club",
    "clubs.add_team",
    "clubs.change_team",
    "clubs.add_clubfile",
    "clubs.change_clubfile",
    "clubs.add_clubmembership",
    "clubs.change_clubmembership",
    # Events
    "events.add_event",
    "events.change_event",
    "events.view_recurringevent",
]
"""Edit and add permissions with some restrictions."""

ADMIN_ROLE_PERMISSIONS = [
    *EDITOR_ROLE_PERMISSIONS,
    # Clubs
    "clubs.delete_team",
    "clubs.delete_clubfile",
    "clubs.delete_clubmembership",
    "clubs.add_clubapikey",
    "clubs.view_clubapikey",
    "clubs.change_clubapikey",
    "clubs.delete_clubapikey",
    # Events
    "events.delete_event",
    "events.add_recurringevent",
    "events.change_recurringevent",
    "events.delete_recurringevent",
]
"""All permissions for a club"""

# Sort permissions lists to use for testing, assertions, etc
VIEWER_ROLE_PERMISSIONS.sort()
EDITOR_ROLE_PERMISSIONS.sort()
ADMIN_ROLE_PERMISSIONS.sort()


INITIAL_CLUB_ROLES: list[RolePayloadType] = [
    {
        "name": "Member",
        "role_type": RoleType.VIEWER,
        "default": True,
    },
    {
        "name": "Officer",
        "role_type": RoleType.ADMIN,
        "default": False,
    },
    {
        "name": "Vice President",
        "role_type": RoleType.ADMIN,
        "default": False,
    },
    {
        "name": "President",
        "role_type": RoleType.ADMIN,
        "default": False,
    },
]

INITIAL_TEAM_ROLES: list[RolePayloadType] = [
    {
        "name": "Member",
        "role_type": RoleType.VIEWER,
        "default": True,
    }
]
