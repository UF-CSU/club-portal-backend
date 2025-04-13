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
    """Check object permissions via api."""

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_object_permission(self, request, view, obj):
        action = getattr(view, "action", None)

        if action == "retrieve":
            self.perms_map["GET"] += ["%(app_label)s.view_%(model_name)s"]

        return super().has_object_permission(request, view, obj)


class ModelViewSetBase(ModelViewSet, ViewSetBase):
    """Base viewset for model CRUD operations."""

    # Enable permissions checking in API
    permission_classes = ViewSetBase.permission_classes + [ObjectViewPermissions]
