from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register("events", viewsets.EventViewset, basename="event")
router.register(
    "recurring-events", viewsets.RecurringEventViewSet, basename="recurringevent"
)
# router.register(
#     r"events/(?P<event_id>.+)/attendance",
#     viewsets.EventAttendanceViewSet,
#     basename="attendance",
# )

app_name = "api-events"

urlpatterns = [path("", include(router.urls))]
