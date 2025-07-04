"""
Define settings for how automated TypeScript generation
should function.
"""

from clubs.serializers import (
    ClubMembershipSerializer,
    ClubPreviewSerializer,
    ClubSerializer,
    ClubTagSerializer,
    TeamSerializer,
)
from events.serializers import EventSerializer
from polls.serializers import PollSerializer
from users.serializers import UserSerializer

SERIALIZERS_CREATE_READ_UPDATE = [
    ClubSerializer,
    ClubMembershipSerializer,
    TeamSerializer,
    EventSerializer,
    UserSerializer,
    PollSerializer,
]
"""
List of serializers to create interfaces for:

- Base object
- Creating object
- Updating object
"""

SERIALIZERS_READONLY = [
    ClubTagSerializer,
    ClubPreviewSerializer,
]
"""
List of serializers to create base interface for only.
"""
