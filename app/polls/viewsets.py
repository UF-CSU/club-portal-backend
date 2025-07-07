from core.abstracts.viewsets import ModelViewSetBase
from polls.models import Poll
from polls.serializers import PollSerializer


class PollViewset(ModelViewSetBase):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
