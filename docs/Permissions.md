# Club Manager Permissions Structure

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
