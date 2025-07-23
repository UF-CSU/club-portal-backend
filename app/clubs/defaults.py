"""
General constants and initial values for club items.
"""

from typing import TypedDict

from clubs.models import RoleType


class RolePayloadType(TypedDict):
    name: str
    default: bool
    role_type: RoleType
    # permissions: list[str]


VIEWER_ROLE_PERMISSIONS = ["clubs.view_club", "events.view_event", "clubs.view_team"]
ADMIN_ROLE_PERMISSIONS = [
    "clubs.view_club",
    "clubs.change_club",
    "events.view_event",
    "events.change_event",
    "clubs.view_team",
    "clubs.change_team",
]


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
