from django.urls import include, path
from rest_framework.routers import DefaultRouter

from polls import viewsets

router = DefaultRouter()
router.register("polls", viewsets.PollViewset, basename="poll")
router.register("poll-previews", viewsets.PollPreviewViewSet, basename="pollpreview")
router.register(
    r"polls/(?P<poll_id>.+)/submissions",
    viewsets.PollSubmissionViewSet,
    basename="pollsubmission",
)
router.register(
    r"polls/(?P<poll_id>.+)/fields", viewsets.PollFieldViewSet, basename="pollfield"
)
router.register(
    r"polls/(?P<poll_id>.+)/fields/(?P<field_id>.+)/choice-options",
    viewsets.PollChoiceOptionViewSet,
    basename="pollchoiceoption",
)

router.register(
    r"polltemplates",
    viewsets.PollTemplateViewSet,
    basename="polltemplate",
)

app_name = "api-polls"

urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
    path(
        "polls/<int:poll_id>/analytics/",
        viewsets.PollAnalyticsView.as_view(),
        name="pollanalytics",
    ),
]
