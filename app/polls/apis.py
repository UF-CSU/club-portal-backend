from django.urls import include, path
from rest_framework.routers import DefaultRouter

from polls import viewsets

router = DefaultRouter()
router.register("polls", viewsets.PollViewset, basename="poll")
router.register(
    r"polls/(?P<poll_id>.+)/submissions",
    viewsets.PollSubmissionViewSet,
    basename="pollsubmission",
)
router.register(
    r"polls/(?P<poll_id>.+)/fields", viewsets.PollFieldViewSet, basename="poll_field"
)

app_name = "api-polls"

urlpatterns = [path("", include(router.urls))]
