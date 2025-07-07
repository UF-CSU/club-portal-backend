"""
Define settings for how automated TypeScript generation
should function.
"""

from clubs.serializers import (
    ClubMembershipSerializer,
    ClubPreviewSerializer,
    ClubSerializer,
    ClubSocialSerializer,
    ClubTagSerializer,
    TeamMembershipSerializer,
    TeamSerializer,
)
from events.serializers import EventHostSerializer, EventSerializer, EventTagSerializer
from polls.serializers import PollSerializer
from users.serializers import SocialProviderSerializer, UserSerializer

SERIALIZERS_CREATE_READ_UPDATE = [
    ClubSerializer,
    ClubMembershipSerializer,
    TeamSerializer,
    TeamMembershipSerializer,
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
    SocialProviderSerializer,
    ClubSocialSerializer,
    EventHostSerializer,
    EventTagSerializer,
]
"""
List of serializers to create base interface for only.
"""
