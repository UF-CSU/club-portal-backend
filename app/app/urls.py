"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from analytics.views import redirect_link_view
from app.settings import DEV

apipatterns = [
    path("schema/club-portal", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path("user/", include("users.apis")),
    path("club/", include("clubs.apis")),
    path("poll/", include("polls.apis")),
    path("event/", include("events.apis")),
    path("analytics/", include("analytics.apis")),
]

urlpatterns = [
    path("", include("core.urls")),
    path("r/<int:link_id>/", redirect_link_view, name="redirect-link"),
    path("admin/", admin.site.urls),
    path("auth/", include("users.authentication.urls")),
    path("auth/", include("django.contrib.auth.urls")),
    path("api/docs/", RedirectView.as_view(url="/api/v1/docs/"), name="api-docs-base"),
    path("api/v1/", include(apipatterns)),
    path("users/", include("users.urls")),
    path("clubs/", include("clubs.urls")),
    path("events/", include("events.urls")),
    path("oauth/", include("allauth.urls"), name="oauth"),
    path("api/oauth/", include("allauth.headless.urls")),
    path("analytics/", include("analytics.urls")),
    path("polls/", include("polls.urls")),
]

if DEV:
    # from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
    # urlpatterns += debug_toolbar_urls()
    urlpatterns.append(
        path("__reload__/", include("django_browser_reload.urls")),
    )
