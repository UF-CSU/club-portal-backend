"""
General constants and initial values for club items.
"""

from typing import TypedDict


class RoleType(TypedDict):
    name: str
    default: bool
    permissions: list[str]


INITIAL_CLUB_ROLES: list[RoleType] = [
    {
        "name": "Member",
        "default": True,
        "permissions": [
            "clubs.view_club",
            "events.view_event",
            "clubs.view_team",
        ],
    },
    {
        "name": "Officer",
        "default": False,
        "permissions": [
            "clubs.view_club",
            "clubs.change_club",
            "events.view_event",
            "events.change_event",
            "clubs.view_team",
            "clubs.change_team",
        ],
    },
]

INITIAL_TEAM_ROLES: list[RoleType] = [
    {
        "name": "Member",
        "default": True,
        "permissions": [],
    }
]
