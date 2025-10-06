from typing import Literal, Optional, TypedDict

from django.db import models
from django.template import loader
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import authentication, filters, permissions
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from app.settings import DJANGO_ENABLE_API_SESSION_AUTH


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

    filterset_class: type
    """Optionally pass a filterset class to define complex filtering."""

    filterset_fields: list
    """Optionally define which fields can be filtered against in the url."""

    filter_backends: list = [DjangoFilterBackend]
    """Define (list) what backends to use for filtering."""

    search_fields: list
    """Define (list) what model fields to search against. Needs `filters.SearchFilter` in `filter_backends` to work."""

    def filter_queryset(self, queryset: models.QuerySet) -> models.QuerySet:
        return super().filter_queryset(queryset)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if DJANGO_ENABLE_API_SESSION_AUTH:
            self.authentication_classes += [authentication.SessionAuthentication]


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

    # def has_object_permission(self, request, view, obj):
    #     queryset = self._queryset(view)
    #     model_cls = queryset.model
    #     user = request.user
    #     perms = self.get_required_object_permissions(request.method, model_cls)
    #     print('required perms:', perms)
    #     print('has perms:', user.has_perms(perms, obj))
    #     print('has perm:', user.has_perm(perms[0], obj))
    #     return super().has_object_permission(request, view, obj)


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

    # # Cache detail view for 2 minutes for each different Authorization header
    # @method_decorator(cache_page(60 * 60 * 2))
    # @method_decorator(vary_on_headers("Authorization"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # # Cache list view for 2 minutes for each different Authorization header
    # @method_decorator(cache_page(60 * 60 * 2))
    # @method_decorator(vary_on_headers("Authorization"))
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


class FilterBackendBase(filters.BaseFilterBackend):
    """Provide additional functionality and typing for the base filter backend."""

    class ParamType(TypedDict):
        name: str
        schema_type: str
        required: Optional[bool] = False
        description: Optional[str] = None

    filter_fields: list[ParamType] = []
    """Define fields to show in documentation."""

    template = "core/filters/query.html"

    def filter_queryset(
        self, request: Request, queryset: models.QuerySet, view: ViewSet
    ):
        return super().filter_queryset(request, queryset, view)

    def to_html(self, request, queryset, view):
        # Used to display query params in browsable api view

        template = loader.get_template(self.template)
        context = {"fields": []}

        for field in self.filter_fields:
            if field.get("schema_type", "string") == "boolean":
                html_field_template = "core/filters/boolean_input.html"
            else:
                html_field_template = "core/filters/text_input.html"

            html_field_template = loader.get_template(html_field_template)

            context["fields"].append(
                {
                    "param": field["name"],
                    "name": field["name"].capitalize().replace("_", " "),
                    "input": html_field_template.render({"field": field}),
                }
            )

        return template.render(context, request)

    def get_schema_operation_parameters(self, view):
        # Used to display query params in swagger spec

        params = super().get_schema_operation_parameters(view)
        params += [
            {
                "name": field["name"],
                "in": "query",
                "required": field.get("required", False),
                "description": field.get("description", ""),
                "schema": {"type": field.get("schema_type", "string")},
            }
            for field in self.filter_fields
        ]

        return params
