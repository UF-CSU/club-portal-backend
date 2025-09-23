"""
Custom forms for clubs.
Form interface is a mixture between Google Forms, Jupyter Notebook,
Gravity Forms (WordPress plugin), and SendGrid.

Google Forms: Mimic form data structure
Jupyter Notebook: Mimic markup capabilities
Gravity Forms: Naming conventions
SendGrid: Versioning (later)

API Inspiration: https://developers.google.com/workspace/forms/api/reference/rest/v1/forms

Structure:
```
Poll
-- Field
-- -- Page Break
-- -- Markup
-- -- Question
-- -- -- Text Input (short, long, rich)
-- -- -- Choice Input (single, multiple)
-- -- -- Range Input
-- -- -- Upload Input
-- -- -- Number Input
```
"""

from datetime import datetime
from typing import ClassVar, Optional

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask
from rest_framework import exceptions

from analytics.models import Link
from clubs.models import Club, ClubFile, ClubScopedModel
from core.abstracts.models import ManagerBase, ModelBase
from events.models import Event, EventType
from users.models import User
from utils.formatting import format_bytes
from utils.helpers import get_full_url


class PollType(models.TextChoices):
    """Different types of polls."""

    STANDARD = "standard", _("Standard")
    TEMPLATE = "template", _("Template")


class PollStatusType(models.TextChoices):
    """Different states the poll can exist in."""

    OPEN = "open", _("Open")
    CLOSED = "closed", _("Closed")
    SCHEDULED = "scheduled", _("Scheduled")
    DRAFT = "draft", _("Draft")
    # CANCELED = "canceled", _("Canceled")


class PollInputType(models.TextChoices):
    """Types of fields a user can add to a poll."""

    TEXT = "text", _("Text")
    CHOICE = "choice", _("Choice")
    SCALE = "scale", _("Scale")
    UPLOAD = "upload", _("Upload")
    NUMBER = "number", _("Number")
    EMAIL = "email", _("Email")
    PHONE = "phone", _("Phone")
    DATE = "date", _("Date")
    TIME = "time", _("Time")
    URL = "url", _("Url")
    CHECKBOX = "checkbox", _("Checkbox")


class PollFieldType(models.TextChoices):
    """Different types of fields that can be added to a poll."""

    QUESTION = "question"
    PAGE_BREAK = "page_break"
    MARKUP = "markup"


class PollTextInputType(models.TextChoices):
    """Different ways of inputing text responses."""

    SHORT = "short", _("Short Text")
    LONG = "long", _("Long Text")
    RICH = "rich", _("Rich Text")


class PollChoiceType(models.TextChoices):
    """Different ways of showing a choice field."""

    DROPDOWN = "dropdown", _("Dropdown Select")
    SELECT = "select", _("Input Select")


class PollUserFieldType(models.TextChoices):
    """User fields that can be populated by values of form questions."""

    NAME = "name", _("Name")
    PHONE = "phone", _("Phone")
    MAJOR = "major", _("Major")
    MINOR = "minor", _("Minor")
    COLLEGE = "college", _("College")
    GRADUATION_DATE = "graduation_date", _("Graduation Date")


class UploadFileType(models.TextChoices):
    """
    Different types of files that can be uploaded.

    Overview: https://www.w3schools.com/tags/att_input_accept.asp
    Complete list: https://www.iana.org/assignments/media-types/media-types.xhtml
    """

    AUDIO = "audio/*", _("Audio")
    VIDEO = "video/*", _("Video")
    IMAGE = "image/*", _("Image")
    PDF = ".pdf", _("Pdf")
    TEXT = ".txt", _("Text")
    WORD = ".docx", _("Word")
    CSV = ".csv", _("Csv")
    EXCEL = ".xlsx,.xls", _("Excel")


class AnswerFieldType(models.TextChoices):
    """Which field to apply the answer value to."""

    TEXT_VALUE = "text_value", _("Text Value")
    NUMBER_VALUE = "number_value", _("Number Value")
    OPTIONS_VALUE = "options_value", _("Options Value")
    BOOLEAN_VALUE = "boolean_value", _("Boolean Value")
    FILE_VALUE = "file_value", _("File Value")


class PollManager(ManagerBase["Poll"]):
    """Manage queries for polls."""

    def create(self, name: str, **kwargs):
        is_published = kwargs.pop("is_published", False)
        poll = super().create(name=name, **kwargs)

        if is_published:
            poll.is_published = True
            poll.save()

        return poll


class Poll(ClubScopedModel, ModelBase):
    """Custom form."""

    name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)
    poll_type = models.CharField(
        choices=PollType.choices, default=PollType.STANDARD, editable=False
    )
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="_poll", blank=True, null=True
    )
    club = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="polls", null=True, blank=True
    )

    status = models.CharField(
        choices=PollStatusType.choices,
        default=PollStatusType.DRAFT,
        editable=False,
    )
    open_at = models.DateTimeField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)

    open_task = models.ForeignKey(
        PeriodicTask,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    close_task = models.ForeignKey(
        PeriodicTask,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # Foreign Relationships
    fields: models.QuerySet["PollField"]
    submissions: models.QuerySet["PollSubmission"]

    # Dynamic properties
    @property
    def questions(self):
        return PollQuestion.objects.filter(field__poll=self).all()

    @cached_property
    def submissions_count(self) -> int:
        return getattr(self, "_submissions_count", None) or self.submissions.count()

    @cached_property
    def last_submission_at(self) -> Optional[datetime]:
        prefetched_last_submission_at = getattr(self, "_last_submission_at", None)
        if prefetched_last_submission_at is not None:
            return prefetched_last_submission_at

        if not self.submissions.all().exists():
            return None
        else:
            return self.submissions.all().order_by("-created_at").first().created_at

    @cached_property
    def submissions_download_url(self):
        return get_full_url(reverse("polls:poll_submissions", args=[self.pk]))

    @property
    def are_tasks_out_of_sync(self):
        """Returns true if open/close schedules need to be synced."""

        if self.open_at is not None and self.open_task is None:
            return True
        elif self.open_at is None and self.open_task is not None:
            return True
        elif self.close_at is not None and self.close_task is None:
            return True
        elif self.close_at is None and self.close_task is not None:
            return True
        elif (
            self.open_at is not None
            and self.open_task is not None
            and self.open_at != self.open_task.clocked.clocked_time
        ):
            return True
        elif (
            self.close_at is not None
            and self.close_task is not None
            and self.close_at != self.close_task.clocked.clocked_time
        ):
            return True

        return False

    @property
    def is_published(self):
        return self.status != PollStatusType.DRAFT

    @is_published.setter
    def is_published(self, value: bool):
        if value is False:
            self.status = PollStatusType.DRAFT
            return

        self.sync_status(override_draft=True, commit=False)

    @property
    def submission_link(self) -> Optional["PollSubmissionLink"]:
        return getattr(self, "_submission_link", None)

    # Overrides
    objects: ClassVar[PollManager] = PollManager()

    def save(self, *args, **kwargs):
        if hasattr(self, "polltemplate"):
            self.poll_type = PollType.TEMPLATE

        self.sync_status(commit=False)

        return super().save(*args, **kwargs)

    def clean(self):
        if (
            self.open_at is not None and self.close_at is not None
        ) and self.open_at > self.close_at:
            raise exceptions.ValidationError(
                "Open date cannot be greater than the close date"
            )

        return super().clean()

    class Meta:
        ordering = ["-open_at"]
        constraints = [
            models.CheckConstraint(
                name="poll_close_date_must_have_start_date",
                check=(
                    ~(models.Q(close_at__isnull=False) & models.Q(open_at__isnull=True))
                ),
            ),
            models.CheckConstraint(
                name="only_poll_templates_allow_null_club",
                check=(
                    ~(
                        models.Q(club__isnull=True)
                        & models.Q(poll_type=PollType.STANDARD)
                    )
                ),
            ),
        ]

    # Methods
    def sync_status(self, override_draft=False, commit=True):
        """Set status based on open/close dates."""

        if not override_draft and self.status == PollStatusType.DRAFT:
            return

        if self.open_at is None and self.close_at is None:
            self.status = PollStatusType.OPEN
        elif self.open_at <= timezone.now() and (
            self.close_at is None or self.close_at > timezone.now()
        ):
            self.status = PollStatusType.OPEN
        elif self.open_at <= timezone.now() and self.close_at <= timezone.now():
            self.status = PollStatusType.CLOSED
        elif self.open_at > timezone.now():
            self.status = PollStatusType.SCHEDULED

        if commit:
            self.save()

    def add_field(self, field_type: PollFieldType):
        """Add new question, markup, or page break to a poll."""

        highest_order = self.fields.order_by("-order")
        if highest_order.exists():
            highest_order = highest_order.first().order
        else:
            highest_order = 1

        return PollField.objects.create(
            poll=self, order=highest_order, field_type=field_type
        )


class PollSubmissionLink(Link):
    """Manage links for poll submissions."""

    poll = models.OneToOneField(
        Poll, on_delete=models.CASCADE, related_name="_submission_link"
    )


class PollTemplateManager(ManagerBase["PollTemplate"]):
    """Manage poll template queries."""

    def create(self, template_name: str, poll_name: str, **kwargs):
        return super().create(template_name=template_name, name=poll_name, **kwargs)


class PollTemplate(Poll):
    """Extension of polls that allow the creation of new polls."""

    template_name = models.CharField()
    event_type = models.CharField(choices=EventType.choices, null=True, blank=True)

    # Overrides
    objects: ClassVar[PollTemplateManager] = PollTemplateManager()


class PollFieldManager(ManagerBase["PollField"]):
    """Manage queries with Poll Fields."""

    def create(self, poll: Poll, **kwargs):

        return super().create(poll=poll, **kwargs)


class PollField(ClubScopedModel, ModelBase):
    """Custom question field for poll forms."""

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="fields")
    field_type = models.CharField(
        choices=PollFieldType.choices, default=PollFieldType.QUESTION
    )
    order = models.IntegerField(blank=True)

    # Dynamic properties
    @property
    def question(self) -> Optional["PollQuestion"]:
        return getattr(self, "_question", None)

    @property
    def markup(self) -> Optional["PollMarkup"]:
        return getattr(self, "_markup", None)

    # Overrides
    objects: ClassVar[PollFieldManager] = PollFieldManager()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.poll} - {self.order}"

    def save(self, *args, **kwargs):
        if self.order is None:
            self.set_order()

        if self.field_type is None:
            if self.question is not None:
                self.field_type = PollFieldType.QUESTION
            elif self.markup is not None:
                self.field_type = PollFieldType.MARKUP
            else:
                self.field_type = PollFieldType.PAGE_BREAK
        return super().save(*args, **kwargs)

    def set_order(self):
        """Set order to be last in list."""

        if self.poll.fields.count() > 0:
            self.order = self.poll.fields.order_by("-order").first().order + 1
        else:
            self.order = 1


class PollMarkup(ClubScopedModel, ModelBase):
    """Store markdown content for a poll."""

    label = models.CharField(null=True, blank=True)
    field = models.OneToOneField(
        PollField, on_delete=models.CASCADE, related_name="_markup"
    )
    content = models.TextField(default="")


class PollQuestionManager(ManagerBase["PollQuestion"]):
    """Manage question queries."""

    def create(
        self,
        field: PollField,
        label: str,
        input_type: PollInputType,
        create_input=False,
        **kwargs,
    ):

        question = super().create(
            field=field, label=label, input_type=input_type, **kwargs
        )

        if not create_input:
            return question

        question.create_input()

        return question


class PollQuestion(ClubScopedModel, ModelBase):
    """
    Record user input.

    Whether a field is required is determined at question (this) level,
    all fields will have defaults.

    Validation is handled at the field level.
    """

    field = models.OneToOneField(
        PollField, on_delete=models.CASCADE, related_name="_question"
    )

    input_type = models.CharField(
        choices=PollInputType.choices, default=PollInputType.TEXT
    )
    label = models.CharField()
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True)
    is_required = models.BooleanField(default=False)

    is_user_lookup = models.BooleanField(default=False, editable=False)
    link_user_field = models.CharField(
        choices=PollUserFieldType.choices, null=True, blank=True
    )

    # TODO: Add is_editable so we can disable editing of certain profile fields like major/minor
    # is_editable = models.BooleaField(default=True, blank=True, editable=False)

    @property
    def input(self):
        match self.input_type:
            case PollInputType.TEXT:
                return self.text_input
            case PollInputType.CHOICE:
                return self.choice_input
            case PollInputType.SCALE:
                return self.scale_input
            case PollInputType.UPLOAD:
                return self.upload_input
            case PollInputType.NUMBER:
                return self.number_input
            case PollInputType.EMAIL:
                return self.email_input
            case PollInputType.PHONE:
                return self.phone_input
            case PollInputType.DATE:
                return self.date_input
            case PollInputType.TIME:
                return self.time_input
            case PollInputType.URL:
                return self.url_input
            case PollInputType.CHECKBOX:
                return self.checkbox_input

        return None

    # Overrides
    @property
    def answer_field(self) -> AnswerFieldType:
        match self.input_type:
            case PollInputType.NUMBER | PollInputType.SCALE:
                return AnswerFieldType.NUMBER_VALUE
            case PollInputType.CHOICE:
                return AnswerFieldType.OPTIONS_VALUE
            case PollInputType.UPLOAD:
                return AnswerFieldType.FILE_VALUE
            case PollInputType.CHECKBOX:
                return AnswerFieldType.BOOLEAN_VALUE
            case _:
                return AnswerFieldType.TEXT_VALUE

    # Foreign relationships
    @property
    def text_input(self) -> Optional["TextInput"]:
        return getattr(self, "_textinput", None)

    @property
    def choice_input(self) -> Optional["ChoiceInput"]:
        return getattr(self, "_choiceinput", None)

    @property
    def scale_input(self) -> Optional["ScaleInput"]:
        return getattr(self, "_scaleinput", None)

    @property
    def upload_input(self) -> Optional["UploadInput"]:
        return getattr(self, "_uploadinput", None)

    @property
    def number_input(self) -> Optional["NumberInput"]:
        return getattr(self, "_numberinput", None)

    @property
    def email_input(self) -> Optional["EmailInput"]:
        return getattr(self, "_emailinput", None)

    @property
    def phone_input(self) -> Optional["PhoneInput"]:
        return getattr(self, "_phoneinput", None)

    @property
    def date_input(self) -> Optional["DateInput"]:
        return getattr(self, "_dateinput", None)

    @property
    def time_input(self) -> Optional["TimeInput"]:
        return getattr(self, "_timeinput", None)

    @property
    def url_input(self) -> Optional["UrlInput"]:
        return getattr(self, "_urlinput", None)

    @property
    def checkbox_input(self) -> Optional["CheckboxInput"]:
        return getattr(self, "_checkboxinput", None)

    # Overrides
    objects: ClassVar[PollQuestionManager] = PollQuestionManager()

    class Meta:
        ordering = ["field", "-id"]

    def __str__(self):
        return self.label

    def clean(self):
        if (
            PollQuestion.objects.filter(
                field__poll=self.field.poll, is_user_lookup=True
            ).count()
            > 1
        ):
            raise exceptions.ValidationError(
                "Can only have one user lookup field per poll."
            )

        elif (
            self.link_user_field is not None
            and PollQuestion.objects.filter(
                field__poll__id=self.field.poll.id, link_user_field=self.link_user_field
            )
            .exclude(id=self.id)
            .count()
            > 0
        ):
            raise exceptions.ValidationError(
                "Cannot have multiple fields set to the same user field."
            )

        elif self.is_user_lookup and not self.is_required:
            self.is_required = True

        return super().clean()

    def delete(self, *args, **kwargs):
        # assert self.is_user_lookup is False, "Cannot delete the user lookup question."

        return super().delete(*args, **kwargs)

    # Methods
    def create_input(self, **kwargs):
        """Create input based on input_type."""

        if self.input is not None:
            return self.input

        match self.input_type:
            case PollInputType.TEXT:
                return TextInput.objects.create(question=self, **kwargs)
            case PollInputType.CHOICE:
                return ChoiceInput.objects.create(question=self, **kwargs)
            case PollInputType.SCALE:
                return ScaleInput.objects.create(question=self, **kwargs)
            case PollInputType.UPLOAD:
                return UploadInput.objects.create(question=self, **kwargs)
            case PollInputType.NUMBER:
                return NumberInput.objects.create(question=self, **kwargs)
            case PollInputType.EMAIL:
                return EmailInput.objects.create(question=self, **kwargs)
            case PollInputType.PHONE:
                return PhoneInput.objects.create(question=self, **kwargs)
            case PollInputType.DATE:
                return DateInput.objects.create(question=self, **kwargs)
            case PollInputType.TIME:
                return TimeInput.objects.create(question=self, **kwargs)
            case PollInputType.URL:
                return UrlInput.objects.create(question=self, **kwargs)
            case PollInputType.CHECKBOX:
                return CheckboxInput.objects.create(question=self, **kwargs)
            case _:
                raise Exception(f"Unrecognized input type {self.input_type}")

    def update_input(self, **kwargs):
        """Update input fields with kwargs based on input_type."""

        if not self.input:
            raise exceptions.ValidationError("No input to update")

        for key, value in kwargs.items():
            setattr(self.input, key, value)

        self.input.save()
        return self.input


class InputBase(ClubScopedModel, ModelBase):
    """Base fields for input objects."""

    question = models.OneToOneField(
        PollQuestion, on_delete=models.CASCADE, related_name="_%(class)s"
    )

    @property
    def poll(self):
        return self.question.field.poll

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.question} - {self.question.input_type}"


class TextInputBase(InputBase):
    """Default validation fields for text inputs."""

    min_length = models.PositiveIntegerField(
        null=True, blank=True, default=1, validators=[MinValueValidator(1)]
    )
    max_length = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        if (
            self.max_length is not None
            and self.min_length is not None
            and self.max_length <= self.min_length
        ):
            raise exceptions.ValidationError(
                {"max_length": "Max length must be greater than min length."}
            )
        return super().clean()


class TextInput(TextInputBase):
    """
    Text input, textarea, or rich text editor.

    If character count is 0, then field is empty, and should
    raise error if the field is required.
    """

    text_type = models.CharField(
        choices=PollTextInputType.choices, default=PollTextInputType.SHORT
    )

    # Overrides
    class Meta:
        constraints = [
            models.CheckConstraint(
                name="min_length_less_than_max_length",
                check=models.Q(min_length__lt=models.F("max_length")),
            ),
        ]


class ChoiceInputManager(ManagerBase["ChoiceInputOption"]):
    """Manage choice input option queries."""

    def create(self, **kwargs):
        options = kwargs.pop("options", None)
        choice_input = super().create(**kwargs)

        if options:
            for option in options:
                ChoiceInputOption.objects.create(input=choice_input, **option)

        return choice_input


class ChoiceInput(InputBase):
    """Dropdown or radio field."""

    is_multiple = models.BooleanField(default=False)
    choice_type = models.CharField(
        choices=PollChoiceType.choices, default=PollChoiceType.DROPDOWN
    )

    # Foreign relations
    selections: models.QuerySet["PollQuestionAnswer"]
    options: models.QuerySet["ChoiceInputOption"]

    # Overrides
    objects: ClassVar[ChoiceInputManager] = ChoiceInputManager()


class ChoiceInputOption(ClubScopedModel, ModelBase):
    """Option element inside select field."""

    input = models.ForeignKey(
        ChoiceInput, on_delete=models.CASCADE, related_name="options"
    )

    order = models.IntegerField(blank=True)
    label = models.CharField(max_length=100)
    value = models.CharField(blank=True, default="", max_length=100)
    image = models.ImageField(null=True, blank=True)
    is_default = models.BooleanField(default=False, blank=True)
    is_other = models.BooleanField(default=False, blank=True)

    # Overrides
    class Meta:
        ordering = ["order", "-id"]
        constraints = [
            models.UniqueConstraint(
                name="unique_default_option_per_choicefield",
                fields=["input", "is_default"],
                condition=models.Q(is_default=True),
            ),
            models.UniqueConstraint(
                name="one_other_option_per_choicefield",
                fields=["input", "is_other"],
                condition=models.Q(is_other=True),
            ),
        ]

    def save(self, *args, **kwargs):
        if self.order is None:
            self.set_order()
        if not self.value or self.value.strip() == "":
            self.value = self.label
        if self.is_other:
            self.value = "other"

        return super().save(*args, **kwargs)

    def clean(self):
        """Validate data before it hits database."""

        # Allow user to only provide label, value will sync
        if self.value is None or self.value.strip() == "":
            self.value = self.label

        if not self.input.options.filter(is_default=True).exists():
            self.is_default = True

        return super().clean()

    # Methods
    def set_order(self):
        """Set order to be last in list."""

        if self.input.options.count() > 0:
            self.order = self.input.options.order_by("-order").first().order + 1
        else:
            self.order = 1


class ScaleInput(InputBase):
    """Slider input."""

    # min_value = models.IntegerField(default=0)
    max_value = models.IntegerField(
        default=10, validators=[MinValueValidator(5), MaxValueValidator(10)]
    )

    left_label = models.CharField(max_length=24, null=True, blank=True)
    right_label = models.CharField(max_length=24, null=True, blank=True)

    # step = models.IntegerField(default=1)
    initial_value = models.IntegerField(default=1)
    # unit = models.CharField(max_length=16, null=True, blank=True)


class UploadInput(InputBase):
    """Upload button, file input."""

    def get_default_upload_filesize():
        """Default 10MB in bytes."""
        return 1024 * 1024 * 10

    file_types = ArrayField(
        base_field=models.CharField(choices=UploadFileType.choices, max_length=32),
        blank=True,
        null=True,
    )
    max_files = models.IntegerField(default=1)
    max_file_size = models.BigIntegerField(
        default=get_default_upload_filesize, blank=True
    )

    @property
    def max_file_size_display(self):
        return format_bytes(self.max_file_size)


class NumberInput(InputBase):
    """Number input, for numeric responses."""

    min_value = models.FloatField(default=0.0)
    max_value = models.FloatField(default=10.0)

    # unit = models.CharField(max_length=16, null=True, blank=True)

    # decimal_places = models.PositiveIntegerField(
    #     default=1, validators=[MinValueValidator(0)]
    # )


class EmailInput(TextInputBase):
    """Text input with email validation."""

    is_school_email = models.BooleanField(default=False, blank=True)


class PhoneInput(InputBase):
    """Text input with phone number validation."""


class DateInput(InputBase):
    """Standard date input."""

    min_value = models.DateField(null=True, blank=True)
    max_value = models.DateField(null=True, blank=True)
    exclude_day = models.BooleanField(default=False, blank=True)


class TimeInput(InputBase):
    """Standard time input."""

    min_value = models.TimeField(null=True, blank=True)
    max_value = models.TimeField(null=True, blank=True)


class UrlInput(TextInputBase):
    """Text input with url validation."""


class CheckboxInput(InputBase):
    """Single checkbox for boolean values."""

    is_consent = models.BooleanField(default=False, blank=True)
    allow_indeterminate = models.BooleanField(default=False, blank=True)
    label = models.CharField(null=True, blank=True, max_length=32)

    def clean(self):
        if self.is_consent and self.allow_indeterminate:
            self.allow_indeterminate = False

        if self.is_consent and not self.question.is_required:
            self.question.is_required = True
            self.question.save()

        return super().clean()


class PollSubmission(ClubScopedModel, ModelBase):
    """Records a person's input for a poll."""

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="submissions")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="poll_submissions",
        null=True,
        blank=True,
    )

    error = models.CharField(null=True, blank=True)
    is_complete = models.BooleanField(default=True, blank=True)

    # Foreign relations
    answers: models.QuerySet["PollQuestionAnswer"]

    # Overrides
    def __str__(self):
        return f"Submission from {self.user or 'anonymous'}"

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            # TODO: Add unique constraint for user/poll submission
            #         models.CheckConstraint(
            #             name="submission_cant_have_error_and_be_complete",
            #             check=(~(models.Q(error__isnull=False) & models.Q(is_complete=True))),
            #         )
        ]

    # Dynamic properties
    @cached_property
    def is_valid(self) -> bool:
        # Is valid if no error and no answers have errors
        if self.error:
            return False

        answers = self.answers.all()
        return all(a.error is None for a in answers)


class PollQuestionAnswerManager(ManagerBase["PollQuestionAnswer"]):
    """Manage queries with poll answers."""

    def create(self, **kwargs):
        options_value = kwargs.pop("options_value", [])

        answer = super().create(**kwargs)

        for value in options_value:
            answer.options_value.add(value)

        return answer

    def update_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        options = defaults.pop("options_value", None)

        submission, created = super().update_or_create(defaults, **kwargs)

        if options:
            submission.options_value.set(options)

        return submission, created


class PollQuestionAnswer(ClubScopedModel, ModelBase):
    """Store info about how a user answered a specific question."""

    question = models.ForeignKey(
        PollQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    submission = models.ForeignKey(
        PollSubmission, on_delete=models.CASCADE, related_name="answers"
    )

    # Answer values
    # Store them separately so calculations can be made in postgres/django orm
    text_value = models.CharField(null=True, blank=True)
    number_value = models.IntegerField(null=True, blank=True)
    options_value = models.ManyToManyField(
        ChoiceInputOption, blank=True, related_name="selections"
    )
    boolean_value = models.BooleanField(null=True, blank=True)
    file_value = models.ForeignKey(
        ClubFile, on_delete=models.CASCADE, null=True, blank=True
    )

    # Only one other option is allowed for a question
    other_option_value = models.CharField(null=True, blank=True)

    # Validation
    error = models.CharField(
        null=True,
        blank=True,
        help_text="Error message if input is not valid.",
        editable=False,
    )

    # Dynamic properties
    @property
    def value(self):
        """Get final value from answer."""
        if self.text_value is not None:
            return self.text_value
        elif self.number_value is not None:
            return self.number_value
        elif self.options_value.exists():
            options = ", ".join(
                list(self.options_value.all().values_list("value", flat=True))
            )
            if self.options_value.filter(is_other=True).exists():
                options.replace("other", self.other_option_value)

            return options
        elif self.boolean_value is not None:
            return self.boolean_value
        elif self.file_value is not None:
            return self.file_value.url
        return None

    @property
    def label(self):
        return self.question.label

    @property
    def is_valid(self) -> bool:
        return self.error is None

    # Overrides
    objects: ClassVar[PollQuestionAnswerManager] = PollQuestionAnswerManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="pollanswer_text_or_number_or_option_set",
                check=(
                    (
                        models.Q(text_value__isnull=False)
                        & models.Q(number_value__isnull=True)
                    )
                    | (
                        models.Q(text_value__isnull=True)
                        & models.Q(number_value__isnull=False)
                    )
                    | (
                        models.Q(text_value__isnull=True)
                        & models.Q(number_value__isnull=True)
                    )
                ),
                violation_error_message='Can only set one of "text", "number", or "options".',
            )
        ]

    def clean(self):
        if not self.pk:
            return super().clean()

        if self.options_value.count() > 0 and (
            self.text_value is not None or self.number_value is not None
        ):
            raise exceptions.ValidationError(
                "Cannot set options value if number or text is set."
            )

        return super().clean()
