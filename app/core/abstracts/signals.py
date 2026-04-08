from utils.permissions import parse_permissions

from core.abstracts.models import RoleBase, RoleType


def on_save_role(sender, instance: RoleBase, created=False, **kwargs):
    """
    When saving roles, sync permissions for role type.

    Ex: When setting role to VIEWER, set permissions as viewer permissions.
    """

    if created:  # Only continue if being updated
        return

    # Clear cached properties
    instance.__dict__.pop("perm_labels", None)

    if instance.role_type == RoleType.CUSTOM:
        # Skip if role type is set to custom
        if instance.cached_role_type != RoleType.CUSTOM:
            instance.cached_role_type = RoleType.CUSTOM
            instance.save()
        return

    perms_mapping = instance.get_permissions_by_role_type()
    permissions = perms_mapping[instance.role_type]

    if instance.cached_role_type != instance.role_type:
        # Role type out of sync, set permissions
        instance.cached_role_type = instance.role_type

        instance.permissions.set(parse_permissions(permissions))

        instance.save()
    elif instance.perm_labels != permissions:
        # Role type in sync, permissions out of sync
        instance.role_type = RoleType.CUSTOM
        instance.cached_role_type = RoleType.CUSTOM
        instance.save()
    else:
        # Role type in sync, permissions in sync
        pass
