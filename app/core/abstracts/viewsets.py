from rest_framework import authentication, permissions
from rest_framework.viewsets import GenericViewSet, ModelViewSet

# User = get_user_model()


class ViewSetBase(GenericViewSet):
    """Provide core functionality for most viewsets."""

    authentication_classes = [
        authentication.TokenAuthentication,
        # authentication.SessionAuthentication,
    ]
    permission_classes = [permissions.IsAuthenticated]


class ObjectViewPermissions(permissions.DjangoObjectPermissions):
    """
    Check object permissions via api.

    Simply provides a wrapper around DRF's DjangoObjectPermissions class
    to allow for easy view/editing of additional permissions per each
    http method type.
    """

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class ModelViewSetBase(ModelViewSet, ViewSetBase):
    """Base viewset for model CRUD operations."""

    # Enable permissions checking in API
    permission_classes = ViewSetBase.permission_classes + [ObjectViewPermissions]
