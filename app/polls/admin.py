"""
Club Polls Admin.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.abstracts.admin import ModelAdminBase, StackedInlineBase
from polls.models import (
    ChoiceInput,
    ChoiceInputOption,
    Poll,
    PollField,
    PollMarkup,
    PollQuestion,
    PollQuestionAnswer,
    PollSubmission,
    PollSubmissionLink,
    ScaleInput,
    TextInput,
    UploadInput,
)
from polls.services import PollService
from utils.formatting import plural_noun_display


class PollFieldInlineAdmin(StackedInlineBase):
    """Manage fields in poll admin."""

    model = PollField
    extra = 0
    readonly_fields = ("question", "edit_link")
    ordering = ("order",)

    def edit_link(self, obj):
        if obj.question:
            return self.as_link(
                obj.question.admin_edit_url,
                text=f"Edit {obj.question} ({obj.question.id})",
            )
        elif obj.markup:
            return self.as_link(
                obj.markup.admin_edit_url, text=f"Edit {obj.markup} ({obj.markup.id})"
            )

        return "-"


class PollSubmissionLinkInlineAdmin(StackedInlineBase):
    """Show submission links for a poll."""

    model = PollSubmissionLink
    extra = 0


class PollAdmin(ModelAdminBase):
    """Manage poll objects in admin."""

    list_display = (
        "__str__",
        "id",
        "field_count",
        "club",
        "event",
        "view_poll",
        "submissions_count",
        "last_submission_at",
    )

    inlines = (
        PollSubmissionLinkInlineAdmin,
        PollFieldInlineAdmin,
    )
    readonly_fields = (
        "field_count",
        "view_poll",
        "submissions_download_link",
    )
    actions = ("sync_submission_links",)

    def field_count(self, obj):
        return obj.fields.count()

    def view_poll(self, obj):
        if obj.id is None:
            return "Not saved yet"
        return mark_safe(
            f"<a href=\"{reverse('polls:poll', kwargs={'poll_id': obj.id})}\" target='_blank'>View Poll</a>"
        )

    def submissions_download_link(self, obj):
        if obj.id is None:
            return "-"
        return self.as_link(obj.submissions_download_url)

    @admin.action(description="Sync submission links for selected polls")
    def sync_submission_links(self, request, queryset):
        for poll in queryset:
            PollService(poll).sync_submission_link()

        self.message_user(
            request,
            f"Synced {plural_noun_display(queryset.count(), 'submission link')}.",
        )

        return


class TextInputInlineAdmin(admin.TabularInline):
    """Manage text inputs in questions admin."""

    model = TextInput
    extra = 0


class ChoiceInputInlineAdmin(admin.TabularInline):
    """Manage choice inputs in questions admin."""

    model = ChoiceInput
    extra = 0


class RangeInputInlineAdmin(admin.TabularInline):
    """Manage range inputs in questions admin."""

    model = ScaleInput
    extra = 0


class UploadInputInlineAdmin(admin.TabularInline):
    """Manage file upload inputs in questions admin."""

    model = UploadInput
    extra = 0


class PollQuestionAdmin(ModelAdminBase):
    """Manage poll questions in admin."""

    list_display = ("__str__", "field", "input_type")

    readonly_fields = ("id", "created_at", "updated_at", "is_user_lookup")

    inlines = (
        TextInputInlineAdmin,
        ChoiceInputInlineAdmin,
        RangeInputInlineAdmin,
        UploadInputInlineAdmin,
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        obj.create_input()


class ChoiceOptionInlineAdmin(admin.TabularInline):
    """Manage option choices in poll choice admin."""

    model = ChoiceInputOption
    extra = 1


class ChoiceInputAdmin(ModelAdminBase):
    """Manage poll choice inputs in admin."""

    list_display = ("__str__", "poll", "options_count")
    inlines = (ChoiceOptionInlineAdmin,)

    def options_count(self, obj):
        return obj.options.count()


class PollQuestionAnswerInlineAdmin(admin.TabularInline):
    """Manage poll question answers in submissions admin."""

    model = PollQuestionAnswer
    extra = 0
    readonly_fields = ("question", "text_value", "number_value", "options_value")
    exclude = ("error",)


class PollSubmissionAdmin(ModelAdminBase):
    """Manage poll submissions in admin."""

    inlines = (PollQuestionAnswerInlineAdmin,)


admin.site.register(Poll, PollAdmin)
admin.site.register(PollQuestion, PollQuestionAdmin)
admin.site.register(PollMarkup)
admin.site.register(ChoiceInput, ChoiceInputAdmin)
admin.site.register(PollSubmission, PollSubmissionAdmin)
