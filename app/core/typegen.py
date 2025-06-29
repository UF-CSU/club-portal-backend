"""
Define settings for how automated TypeScript generation
should function.
"""

from clubs.serializers import (
    ClubMembershipSerializer,
    ClubSerializer,
    TeamSerializer,
    ClubPreviewSerializer,
    ClubTagSerializer,
)
from events.serializers import EventSerializer
from users.serializers import UserSerializer

SERIALIZERS_CREATE_READ_UPDATE = [
    ClubSerializer,
    ClubMembershipSerializer,
    TeamSerializer,
    EventSerializer,
    UserSerializer,
    ClubTagSerializer,
]
"""
List of serializers to create interfaces for:

- Base object
- Creating object
- Updating object
"""

SERIALIZERS_READONLY = [
    ClubPreviewSerializer,
]
"""
List of serializers to create base interface for only.
"""
