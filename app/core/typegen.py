"""
Define settings for how automated TypeScript generation
should function.
"""

from clubs.serializers import (
    ClubFileSerializer,
    ClubMemberSerializer,
    ClubMembershipCreateSerializer,
    ClubPhotoSerializer,
    ClubPreviewSerializer,
    ClubSerializer,
    ClubSocialSerializer,
    ClubTagSerializer,
    TeamMembershipSerializer,
    TeamSerializer,
)
from events.serializers import (
    EventHeatmapSerializer,
    EventHostSerializer,
    EventPreviewSerializer,
    EventSerializer,
    RecurringEventSerializer,
)
from lib.serializer_typegen import InputSerializerType
from polls.serializers import (
    CheckboxInputSerializer,
    ChoiceInputOptionSerializer,
    ChoiceInputSerializer,
    DateInputSerializer,
    EmailInputSerializer,
    NumberInputSerializer,
    PhoneInputSerializer,
    PollFieldSerializer,
    PollPreviewSerializer,
    PollQuestionSerializer,
    PollSerializer,
    PollSubmissionAnswerSerializer,
    PollSubmissionSerializer,
    ScaleInputSerializer,
    TextInputSerializer,
    TimeInputSerializer,
    UploadInputSerializer,
    UrlInputSerializer,
)
from users.serializers import SocialProviderSerializer, UserSerializer

SERIALIZERS_CREATE_READ_UPDATE: list[InputSerializerType] = [
    # Club types
    ClubSerializer,
    (
        ClubMemberSerializer,
        ClubMembershipCreateSerializer,
        ClubMemberSerializer,
    ),
    ClubFileSerializer,
    ClubPhotoSerializer,
    TeamSerializer,
    TeamMembershipSerializer,
    # Event types
    EventSerializer,
    EventHostSerializer,
    RecurringEventSerializer,
    # Poll types
    PollSerializer,
    PollPreviewSerializer,
    PollFieldSerializer,
    PollQuestionSerializer,
    TextInputSerializer,
    ChoiceInputSerializer,
    ChoiceInputOptionSerializer,
    ScaleInputSerializer,
    UploadInputSerializer,
    NumberInputSerializer,
    EmailInputSerializer,
    PhoneInputSerializer,
    DateInputSerializer,
    TimeInputSerializer,
    UrlInputSerializer,
    CheckboxInputSerializer,
    PollSubmissionSerializer,
    PollSubmissionAnswerSerializer,
    # Other types
    UserSerializer,
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
    EventHeatmapSerializer,
    EventPreviewSerializer,
]
"""
List of serializers to create base interface for only.
"""
