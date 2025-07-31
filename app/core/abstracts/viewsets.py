from typing import Literal

from django.db import models
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import authentication, permissions
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet


class ViewSetBase(GenericViewSet):
    """
    Provide core functionality, additional type hints, and improved documentaton for viewsets.
    """

    authentication_classes = [authentication.TokenAuthentication]
    """Determines how a user is considered logged in, or authenticated."""

    permission_classes = [permissions.IsAuthenticated]
    """Determines what a user can do."""

    action: Literal["list", "create", "retrieve", "update", "partial_update", "destroy"]
    """
    What request method is being called for the viewset.

    Learn more:
    - https://www.django-rest-framework.org/api-guide/viewsets/#introspecting-viewset-actions
    - https://testdriven.io/blog/drf-views-part-3/
    """

    detail: bool
    """
    Indicates if the current action is configured for a list or detail view.
    This is irrespective of the request method, detail views include the object's id
    in the url, whereas the list view does not include the id.
    """

    request: Request
    """The incomming request."""

    kwargs: dict
    """
    URL arguments passed in as parameters or query parameters.
    They are defined in the same place the url is defined.
    """

    filterset_class = None
    """Optionally pass a filterset class to define complex filtering."""

    filterset_fields = []
    """Optionally define which fields can be filtered against in the url."""

    def filter_queryset(self, queryset: models.QuerySet) -> models.QuerySet:
        return super().filter_queryset(queryset)


class ObjectViewPermissions(permissions.DjangoObjectPermissions):
    """
    Check object permissions via api.

    Simply provides a wrapper around DRF's DjangoObjectPermissions class
    to allow for easy view/editing of additional permissions per each
    http method type.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class ObjectViewDetailsPermissions(ObjectViewPermissions):
    """
    Overrides custom `ObjectViewPermissions` class to also require
    the `view_model_details` permission when viewing an object.
    """

    perms_map = {
        **ObjectViewPermissions.perms_map,
        "GET": [
            *ObjectViewPermissions.perms_map["GET"],
            "%(app_label)s.view_%(model_name)s_details",
        ],
    }


class ModelViewSetBase(ModelViewSet, ViewSetBase):
    """Base viewset for model CRUD operations."""

    # TODO: Could self.get_object_permissions be used to optimize club perm checking?

    # Enable permissions checking in API
    permission_classes = ViewSetBase.permission_classes + [ObjectViewPermissions]

    # Cache detail view for 2 minutes for each different Authorization header
    @method_decorator(cache_page(60 * 60 * 2))
    @method_decorator(vary_on_headers("Authorization"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # Cache list view for 2 minutes for each different Authorization header
    @method_decorator(cache_page(60 * 60 * 2))
    @method_decorator(vary_on_headers("Authorization"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CustomLimitOffsetPagination(LimitOffsetPagination):
    """Defines custom pagination setup."""

    default_limit = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "offset": self.offset,
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        res_schema = super().get_paginated_response_schema(schema)

        res_schema["properties"] = {
            "offset": {
                "type": "integer",
                "example": 0,
            },
            **res_schema["properties"],
        }

        return res_schema
