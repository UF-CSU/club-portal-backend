import json
import logging
from functools import update_wrapper
from typing import Literal, Optional

from django.contrib import admin
from django.db import models
from django.http import FileResponse, HttpRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.urls.resolvers import URLPattern
from django.utils.safestring import mark_safe
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer

from core.abstracts.models import ModelBase
from querycsv.serializers import CsvModelSerializer
from querycsv.services import QueryCsvService
from querycsv.views import QueryCsvViewSet
from utils.admin import get_admin_context, get_model_admin_reverse


class AdminBase:
    """Common fields, utilities for model admin, inline admin, etc."""

    admin_name = "admin"

    def get_admin_url(
        self,
        model: models.Model,
        url_context: Literal[
            "changelist", "add", "history", "delete", "change"
        ] = "changelist",
        admin_name=None,
        as_link=False,
        link_text=None,
    ):
        """Given a model, return a link to the appropriate admin page."""
        admin_name = admin_name or self.admin_name
        url = get_model_admin_reverse(admin_name, model, url_context)

        if url_context in ["change", "history", "delete"]:
            url = reverse(url, args=[model.id])
        else:
            url = reverse(url)

        if as_link:
            return self.as_link(url, link_text or url)

        return url

    def as_link(self, url, text=None):
        """Create anchor tag for a url."""
        text = text or url

        return mark_safe(f'<a href="{url}" target="_blank">{text}</a>')

    def as_image(self, image: models.ImageField):
        if not image:
            return None

        return mark_safe(
            "<svg width='90' height='90' style='background-color:white'>"
            f"<image  xlink:href={image.url} width='100%'>"
            "</svg>"
        )

    def as_model_link(self, obj: ModelBase, text="%(model)s"):
        """Show object as a link to it's detail/edit page."""

        text = text % {"model": obj.__str__()}
        return self.as_link(obj.admin_edit_url, text=text)

    def as_json(self, obj):
        """
        Convert obj to html json format.

        Reference: https://daniel.feldroy.com/posts/pretty-formatting-json-django-admin
        """

        if obj is None:
            return None

        if isinstance(obj, dict) or isinstance(obj, list):
            obj = json.dumps(obj)

        response = json.dumps(json.loads(obj), indent=2)

        formatter = HtmlFormatter()

        response = highlight(response, JsonLexer(), formatter)
        response = response.replace("\\n", "<br>")
        style = "<style>" + formatter.get_style_defs() + "</style><br>"

        return mark_safe(style + response)


class ModelAdminBase(AdminBase, admin.ModelAdmin):
    """Base class for all model admins."""

    prefetch_related_fields = ()
    """Makes another query to select a set of related objects."""
    select_related_fields = ()
    """Uses SQL Join to select a single related object."""

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    object_tools = ()

    formfield_overrides = {}

    change_list_template = "admin/core/change_list.html"
    csv_serializer_class: Optional[CsvModelSerializer] = None
    """Serializer to use for csv uploads"""

    #################################
    # == Django Method Overrides == #
    #################################

    def __init__(self, model: type, admin_site: admin.AdminSite | None) -> None:
        super().__init__(model, admin_site)

        # If serializer is set, enable certain features
        if self.csv_serializer_class is not None:
            self.csv_svc = QueryCsvService(self.csv_serializer_class)

            def get_reverse(name: str = "changelist"):
                return f"{self.admin_name}:{self._url_name(name)}"

            self.csv_views = QueryCsvViewSet(
                serializer_class=self.csv_serializer_class, get_reverse=get_reverse
            )

            self.actions += ("download_csv",)
            self.object_tools += (
                {
                    "url": "%s:%s_%s_upload"
                    % (self.admin_name, self.opts.app_label, self.opts.model_name),
                    "label": "Upload Data",
                },
            )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.prefetch_related(*self.prefetch_related_fields).select_related(
            *self.select_related_fields
        )
        # if len(self.prefetch_related_fields) > 0 or len(self.select_related_fields) > 0:
        # else:
        #     return qs

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, str] | None = None
    ) -> TemplateResponse:
        context = {
            **(extra_context or {}),
            "object_tools": self.object_tools,
        }

        return super().changelist_view(request, extra_context=context)

    def get_urls(self) -> list[URLPattern]:
        """Extends django's default functionality to add custom urls."""
        from django.urls import path

        # Start duplicated django code ###############
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        # End duplicated django code #################

        # Custom Url Definitions
        ########################
        urls = [
            path("upload/", wrap(self.upload_csv), name=self._url_name("upload")),
            path(
                "upload/<int:id>/headermapping",
                wrap(self.map_upload_csv_headers),
                name=self._url_name("upload_headermapping"),
            ),
            path(
                "csv-template/",
                wrap(self.download_csv_template),
                name=self._url_name("csv_template"),
            ),
            path(
                "csv-template/<path:include_fields>",
                wrap(self.download_csv_template),
                name=self._url_name("csv_template"),
            ),
        ] + super().get_urls()

        return urls

    ##############################
    # == Custom Admin Methods == #
    ##############################

    def _url_name(self, url_context="changelist"):
        """Get url name to reverse for this admin class."""
        info = self.opts.app_label, self.opts.model_name, url_context

        return "%s_%s_%s" % info

    def upload_csv(self, request: HttpRequest, extra_context=None):
        """Custom action for uploading csvs through admin."""

        context = {
            **get_admin_context(request, extra_context),
            "object_name": self.opts.object_name,
            "verbose_name_plural": self.opts.verbose_name_plural,
        }

        return self.csv_views.upload_csv(request, extra_context=context)

    def map_upload_csv_headers(self, request: HttpRequest, id: int, extra_context=None):
        """Given a csv upload job, allow admin to define custom field mappings."""

        context = {**get_admin_context(request, extra_context)}
        return self.csv_views.map_upload_csv_headers(request, id, extra_context=context)

    def download_csv_template(self, request: HttpRequest):
        """Get template for csv uploads."""

        include_fields = request.GET.get("fields", None)

        filepath = self.csv_svc.get_csv_template(field_types=include_fields)
        return FileResponse(open(filepath, "rb"))

    ##############################
    # == Custom Admin Actions == #
    ##############################

    @admin.action(description="Download selection as CSV")
    def download_csv(self, request, queryset):
        """Download queryset of objects."""

        if self.csv_serializer_class is None:
            self.message_user(
                request,
                "Unable to download objects without a serializer.",
                logging.WARNING,
            )
            return redirect(f"{self.admin_name}:{self._url_name()}")

        filepath = self.csv_svc.download_csv(queryset)
        return FileResponse(open(filepath, "rb"))


class InlineBase(AdminBase):
    extra = 0
    formfield_overrides = {}


class StackedInlineBase(InlineBase, admin.StackedInline):
    """Display fk related objects as cards, form flowing down."""


class TabularInlineBase(InlineBase, admin.TabularInline):
    """Display fk related objects in a table, fields flowing horizontally in rows."""
