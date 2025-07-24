from typing import Literal

from rest_framework import authentication, permissions
from rest_framework.viewsets import GenericViewSet, ModelViewSet

# User = get_user_model()


class ViewSetBase(GenericViewSet):
    """Provide core functionality for most viewsets."""

    # Setting types for properties set by drf, read more:
    # - https://www.django-rest-framework.org/api-guide/viewsets/#introspecting-viewset-actions,
    # - https://testdriven.io/blog/drf-views-part-3/
    action: Literal["list", "create", "retrieve", "update", "partial_update", "destroy"]
    """What request method is being called for the viewset."""

    detail: bool
    """Indicates if the current action is configured for a list or detail view."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]


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

    # Enable permissions checking in API
    permission_classes = ViewSetBase.permission_classes + [ObjectViewPermissions]

    # TODO: Could self.get_object_permissions be used to optimize club perm checking?
