from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register("events", viewsets.EventViewset, basename="event")

app_name = "api-events"

urlpatterns = [path("", include(router.urls))]
