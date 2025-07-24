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


VIEWER_ROLE_PERMISSIONS = [
    # Clubs
    "clubs.view_club_details",
    "clubs.view_team",
    "clubs.view_clubfile",
    "clubs.view_clubmembership",
    # Events
    "events.view_private_event",
]
ADMIN_ROLE_PERMISSIONS = [
    *VIEWER_ROLE_PERMISSIONS,
    # Clubs
    "clubs.change_club",
    "clubs.add_team",
    "clubs.change_team",
    "clubs.delete_team",
    "clubs.add_clubfile",
    "clubs.change_clubfile",
    "clubs.delete_clubfile",
    "clubs.add_clubmembership",
    "clubs.change_clubmembership",
    "clubs.delete_clubmembership",
    "clubs.add_clubapikey",
    "clubs.view_clubapikey",
    "clubs.change_clubapikey",
    "clubs.delete_clubapikey",
    # Events
    "events.add_event",
    "events.change_event",
    "events.delete_event",
    "events.view_recurringevent",
    "events.add_recurringevent",
    "events.change_recurringevent",
    "events.delete_recurringevent",
]

# Sort permissions lists to use for testing, assertions, etc
VIEWER_ROLE_PERMISSIONS.sort()
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
