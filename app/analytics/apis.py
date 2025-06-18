"""
URL Patterns for links REST API.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from analytics import viewsets

from . import views
router = DefaultRouter()

router.register("links", viewsets.LinkViewSet, basename="link")

router.register("qrcode", viewsets.QrViewSet, basename="qrcode")

app_name = "api-links"

urlpatterns = [
    path("", include(router.urls)),

]