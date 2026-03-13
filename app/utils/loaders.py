from django.template.loaders.app_directories import Loader
from django.template.utils import get_app_template_dirs


class SQLLoader(Loader):
    """Loader that reads from the sql directory within each app to find sql files"""

    def get_dirs(self):
        return get_app_template_dirs("sql")
