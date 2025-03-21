from django.urls import include, path
from rest_framework.routers import DefaultRouter

from clubs.polls.viewsets import PollViewset

router = DefaultRouter()
router.register("polls", PollViewset, basename="polls")

app_name = "api-clubpolls"

urlpatterns = [path("", include(router.urls))]
