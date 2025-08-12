"""
Define settings for how automated TypeScript generation
should function.
"""

from clubs.serializers import (
    ClubFileSerializer,
    ClubMembershipCreateSerializer,
    ClubMembershipSerializer,
    ClubPhotoSerializer,
    ClubPreviewSerializer,
    ClubSerializer,
    ClubSocialSerializer,
    ClubTagSerializer,
    TeamMembershipSerializer,
    TeamSerializer,
)
from events.serializers import (
    EventAttendanceSerializer,
    EventHostSerializer,
    EventSerializer,
    EventTagSerializer,
    RecurringEventSerializer,
)
from lib.serializer_typegen import InputSerializerType
from polls.serializers import (
    PollChoiceInputOptionSerializer,
    PollChoiceInputSerializer,
    PollFieldSerializer,
    PollNumberInputSerializer,
    PollQuestionSerializer,
    PollRangeInputSerializer,
    PollSerializer,
    PollSubmissionAnswerSerializer,
    PollSubmissionSerializer,
    PollTextInputSerializer,
    PollUploadInputSerializer,
)
from users.serializers import SocialProviderSerializer, UserSerializer

SERIALIZERS_CREATE_READ_UPDATE: list[InputSerializerType] = [
    ClubSerializer,
    (
        ClubMembershipSerializer,
        ClubMembershipCreateSerializer,
        ClubMembershipSerializer,
    ),
    ClubFileSerializer,
    ClubPhotoSerializer,
    TeamSerializer,
    TeamMembershipSerializer,
    EventSerializer,
    EventHostSerializer,
    RecurringEventSerializer,
    EventAttendanceSerializer,
    UserSerializer,
    PollSerializer,
    PollFieldSerializer,
    PollQuestionSerializer,
    PollTextInputSerializer,
    PollChoiceInputSerializer,
    PollChoiceInputOptionSerializer,
    PollRangeInputSerializer,
    PollUploadInputSerializer,
    PollNumberInputSerializer,
    PollSubmissionSerializer,
    PollSubmissionAnswerSerializer,
]
"""
List of serializers to create interfaces for:

- Base object
- Creating object
- Updating object
"""

SERIALIZERS_READONLY: list[InputSerializerType] = [
    ClubTagSerializer,
    ClubPreviewSerializer,
    SocialProviderSerializer,
    ClubSocialSerializer,
    ClubPhotoSerializer,
    EventTagSerializer,
]
"""
List of serializers to create base interface for only.
"""
