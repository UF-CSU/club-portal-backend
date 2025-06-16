"""
URL Patterns for links REST API.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from analytics import viewsets

from . import views
router = DefaultRouter()

router.register("links", viewsets.LinkViewSet, basename="link")

app_name = "api-links"

urlpatterns = [
    path("links/", include(router.urls),),

]