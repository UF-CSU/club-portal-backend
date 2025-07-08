from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets
from . import views

router = DefaultRouter()
router.register("events", viewsets.EventViewset, basename="event")

app_name = "api-events"

urlpatterns = [
    path("", include(router.urls)),
    path("event-tags/", views.get_event_tags, name="event-tags"),
    
]
