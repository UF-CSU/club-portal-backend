from core.abstracts.models import RoleBase, RoleType
from utils.permissions import parse_permissions


def on_save_role(sender, instance: RoleBase, created=False, **kwargs):
    """
    When saving roles, sync permissions for role type.

    Ex: When setting role to VIEWER, set permissions as viewer permissions.
    """

    if created:  # Only continue if being updated
        return

    if instance.role_type == RoleType.CUSTOM:
        # Skip if role type is set to custom
        if instance.cached_role_type != RoleType.CUSTOM:
            instance.cached_role_type = RoleType.CUSTOM
            instance.save()
        return

    if instance.cached_role_type != instance.role_type:
        # Role type out of sync, set permissions
        instance.cached_role_type = instance.role_type

        perms_mapping = instance.get_permissions_by_role_type()
        permissions = parse_permissions(perms_mapping[instance.role_type])
        instance.permissions.set(permissions)

        instance.save()
    elif instance.perm_labels != permissions:
        # Role type in sync, permissions out of sync
        instance.role_type = RoleType.CUSTOM
        instance.cached_role_type = RoleType.CUSTOM
        instance.save()
    else:
        # Role type in sync, permissions in sync
        pass