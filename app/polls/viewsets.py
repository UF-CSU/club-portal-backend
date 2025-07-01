from polls.models import Poll
from polls.serializers import PollSerializer
from core.abstracts.viewsets import ModelViewSetBase


class PollViewset(ModelViewSetBase):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
