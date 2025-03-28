"""
Club Polls Admin.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from clubs.polls.models import (
    ChoiceInput,
    ChoiceInputOption,
    Poll,
    PollField,
    PollInputType,
    PollMarkup,
    PollQuestion,
    PollSubmission,
    RangeInput,
    TextInput,
    UploadInput,
)


class PollFieldInlineAdmin(admin.StackedInline):
    """Manage fields in poll admin."""

    model = PollField
    extra = 0
    readonly_fields = ("question",)
    ordering = ("order",)


class PollAdmin(admin.ModelAdmin):
    """Manage poll objects in admin."""

    list_display = ("__str__", "field_count", "view_poll")

    inlines = (PollFieldInlineAdmin,)
    readonly_fields = ("field_count", "view_poll")

    def field_count(self, obj):
        return obj.fields.count()

    def view_poll(self, obj):
        return mark_safe(
            f"<a href=\"{reverse('clubs:polls:poll', args=[obj.id])}\" target='_blank'>View Poll</a>"
        )


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

    model = RangeInput
    extra = 0


class UploadInputInlineAdmin(admin.TabularInline):
    """Manage file upload inputs in questions admin."""

    model = UploadInput
    extra = 0


class PollQuestionAdmin(admin.ModelAdmin):
    """Manage poll questions in admin."""

    list_display = ("__str__", "field", "input_type", "widget")

    inlines = (
        TextInputInlineAdmin,
        ChoiceInputInlineAdmin,
        RangeInputInlineAdmin,
        UploadInputInlineAdmin,
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.input_type == PollInputType.TEXT and obj.text_input is None:
            TextInput.objects.create(question=obj)
        elif obj.input_type == PollInputType.CHOICE and obj.choice_input is None:
            ChoiceInput.objects.create(question=obj)
        elif obj.input_type == PollInputType.RANGE and obj.range_input is None:
            RangeInput.objects.create(question=obj)
        elif obj.input_type == PollInputType.UPLOAD and obj.upload_input is None:
            UploadInput.objects.create(question=obj)


class ChoiceOptionInlineAdmin(admin.TabularInline):
    """Manage option choices in poll choice admin."""

    model = ChoiceInputOption
    extra = 1


class ChoiceInputAdmin(admin.ModelAdmin):
    """Manage poll choice inputs in admin."""

    list_display = ("__str__", "options_count")
    inlines = (ChoiceOptionInlineAdmin,)

    def options_count(self, obj):
        return obj.options.count()


admin.site.register(Poll, PollAdmin)
admin.site.register(PollQuestion, PollQuestionAdmin)
admin.site.register(PollMarkup)
admin.site.register(ChoiceInput, ChoiceInputAdmin)
admin.site.register(PollSubmission)
