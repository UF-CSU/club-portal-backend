# Permissions Structure

## Django Default Permissions

Django has a set of default permissions for each model:

- `app.add_model`
- `app.change_model`
- `app.delete_model`
- `app.view_model`

With `app` being the name of the module/app (like `users`, `clubs`, etc), and `model` being the name of the model (like `user`, `club`, etc).

## Resources

- <https://testdriven.io/blog/django-permissions/>
- <https://docs.djangoproject.com/en/5.1/ref/contrib/auth/>

## Roles

### Model Hierarchy

1. Group
2. Member
3. Role

Role has a many-to-many field `permissions` to Permission objects. You can get a Permission object from a `perm_label` using the `get_permission` method, where the label follows the format mentioned above (ex: `app.add_model`).

To make it more concrete, here's how the models look for a club:

1. `Club`
2. `ClubMembership`
3. `ClubRole`

### Role Type

Roles can be either custom or be one of the following "preset" types:
1. FOLLOWER
2. VIEWER
3. EDITOR
4. ADMIN

Role models define the permissions associated with these presets through the `get_permissions_by_role_type` method.

## API

The roles that a member has are returned in the member detail route (ex: `GET /clubs/<id>/members`). **Only the name of the role is returned**, the permissions need to be retrieved from the role detail route (ex: `GET /clubs/<id>/roles`).

A member's roles can be modified through the member detail route. However, the roles that you can add to a user is limited by the roles that you currently have. Your role must supersede (contain all of the permissions of) the roles that you are trying to add. For example, if you're an EDITOR, you can add the FOLLOWER, VIEWER, or EDITOR roles to a member, but not ADMIN.

A role's permissions can be modified through the role detail route. However, the permissions that you are trying to add is limited by the permissions that you currently have. You must have all the permissions that you are trying to add. For example, if you're an ADMIN, you can add any permission to a role, while if you're an EDITOR, you won't be able to add ADMIN-only permissions.

Obviously, this only applies if you have the permissions to modify members/roles.