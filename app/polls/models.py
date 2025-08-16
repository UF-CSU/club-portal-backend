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
from django.core import exceptions
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask

from clubs.models import Club
from core.abstracts.models import ManagerBase, ModelBase
from events.models import Event, EventType
from users.models import User
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

    TEXT = "text"
    CHOICE = "choice"
    RANGE = "range"
    UPLOAD = "upload"
    NUMBER = "number"


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

    DROPDOWN = "select", _("Dropdown Select")
    SELECT = "radio", _("Input Select")


# class QuestionCustomType(models.TextChoices):
#     """Categorize different types of text fields."""

#     NAME = "name", _("Name")
#     EMAIL = "email", _("Email")
#     UFL_EMAIL = "ufl_email", _("UFL Email")
#     MAJOR = "major", _("Major")
#     MINOR = "minor", _("Minor")
#     COLLEGE = "college", _("College")
#     PHONE = "phone", _("Phone")
#     GRADUATION_DATE = "graduation_year", _("Graduation Year")
#     DEPARTMENT = "department", _("Department")


class PollUserFieldType(models.TextChoices):
    """User fields that can be populated by values of form questions."""

    NAME = "name", _("Name")
    # EMAIL = "email", _("Email")
    # SCHOOL_EMAIL = "school_email", _("School Email")
    MAJOR = "major", _("Major")
    MINOR = "minor", _("Minor")
    COLLEGE = "college", _("College")
    PHONE = "phone", _("Phone")
    GRADUATION_YEAR = "graduation_date", _("Graduation Year")


class PollManager(ManagerBase["Poll"]):
    """Manage queries for polls."""

    def create(self, name: str, **kwargs):
        is_published = kwargs.pop("is_published", False)
        poll = super().create(name=name, **kwargs)

        if is_published:
            poll.is_published = True
            poll.save()

        return poll


class Poll(ModelBase):
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

    @property
    def submissions_count(self):
        return self.submissions.count()

    @property
    def last_submission_at(self) -> Optional[datetime]:
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

    # Overrides
    objects: ClassVar[PollManager] = PollManager()

    def save(self, *args, **kwargs):
        if hasattr(self, "polltemplate"):
            self.poll_type = PollType.TEMPLATE

        self.sync_status(commit=False)

        # if self.open_at is not None and self.status == PollStatusType.DRAFT:
        #     # Set status to scheduled if just added open at date
        #     self.status = PollStatusType.SCHEDULED
        # elif self.open_at is None and self.status == PollStatusType.OPEN:
        #     # If user set status to open, automatically set open_at to now
        #     self.open_at = timezone.now()

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


class PollField(ModelBase):
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

    def clean(self):
        """
        Validate data before it hits database.
        Sends Validation Error before database sends Integrety Error,
        has better UX.
        """

        # Check order field
        # order_query = PollField.objects.filter(poll=self.poll, order=self.order)
        # if order_query.count() > 1:
        #     raise exceptions.ValidationError(
        #         f"Multiple fields are set to order {self.order}."
        #     )

        return super().clean()

    def save(self, *args, **kwargs):
        if self.order is None:
            self.set_order()

        if self.field_type is None:
            if self.question is not None:
                self.field_type = PollFieldType.QUESTION
            elif self.markup is not None:
                self.field_type = PollFieldType.MARKUP
            elif self.page_break is not None:
                self.field_type = PollFieldType.PAGE_BREAK

        return super().save(*args, **kwargs)

    def set_order(self):
        """Set order to be last in list."""

        if self.poll.fields.count() > 0:
            self.order = self.poll.fields.order_by("-order").first().order + 1
        else:
            self.order = 1


class PollMarkup(ModelBase):
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

        match input_type:
            case PollInputType.TEXT:
                TextInput.objects.create(question=question)
            case PollInputType.CHOICE:
                ChoiceInput.objects.create(question=question)
            case PollInputType.RANGE:
                RangeInput.objects.create(question=question)
            case PollInputType.UPLOAD:
                UploadInput.objects.create(question=question)
            case PollInputType.NUMBER:
                NumberInput.objects.create(question=question)

        return question


class PollQuestion(ModelBase):
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

    # custom_type = models.CharField(
    #     choices=QuestionCustomType.choices, null=True, blank=True
    # )

    is_user_lookup = models.BooleanField(default=False, editable=False)
    link_user_field = models.CharField(
        choices=PollUserFieldType.choices, null=True, blank=True
    )

    @property
    def html_name(self):
        return f"field-{self.field.id}"

    @property
    def html_id(self):
        if self.input is None:
            return "input-unknown"
        return f"input-{self.input.id}"

    @property
    def input(self):
        match self.input_type:
            case PollInputType.TEXT:
                return self.text_input
            case PollInputType.CHOICE:
                return self.choice_input
            case PollInputType.RANGE:
                return self.range_input
            case PollInputType.UPLOAD:
                return self.upload_input
            case PollInputType.NUMBER:
                return self.number_input

        return None

    @property
    def widget(self):
        if not self.input:
            return None

        return self.input.widget

    # Foreign relationships
    @property
    def text_input(self) -> Optional["TextInput"]:
        return getattr(self, "_text_input", None)

    @property
    def choice_input(self) -> Optional["ChoiceInput"]:
        return getattr(self, "_choice_input", None)

    @property
    def range_input(self) -> Optional["RangeInput"]:
        return getattr(self, "_range_input", None)

    @property
    def upload_input(self) -> Optional["UploadInput"]:
        if not hasattr(self, "_upload_input"):
            return None

        return self._upload_input

    @property
    def number_input(self) -> Optional["NumberInput"]:
        if not hasattr(self, "_number_input"):
            return None

        return self._number_input

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

        return super().clean()

    def delete(self, *args, **kwargs):
        assert self.is_user_lookup is False, "Cannot delete the user lookup question."

        return super().delete(*args, **kwargs)


class TextInput(ModelBase):
    """
    Text input, textarea, or rich text editor.

    If character count is 0, then field is empty, and should
    raise error if the field is required.
    """

    question = models.OneToOneField(
        PollQuestion, on_delete=models.CASCADE, related_name="_text_input"
    )

    text_type = models.CharField(
        choices=PollTextInputType.choices, default=PollTextInputType.SHORT
    )
    min_length = models.PositiveIntegerField(
        null=True, blank=True, default=1, validators=[MinValueValidator(1)]
    )
    max_length = models.PositiveIntegerField(null=True, blank=True)

    @property
    def widget(self):
        return PollTextInputType(self.text_type).label

    # Overrides
    class Meta:
        constraints = [
            models.CheckConstraint(
                name="min_length_less_than_max_length",
                check=models.Q(min_length__lt=models.F("max_length")),
            ),
        ]


# class EmailInput(ModelBase):
#     pass

# class PhoneInput(ModelBase):
#     pass

# class DateInput(ModelBase):
#     pass

# class TimeInput(ModelBase):
#     pass

# class UrlInput(ModelBase):
#     pass

# class CheckboxInput(ModelBase):
#     pass


class ChoiceInput(ModelBase):
    """Dropdown or radio field."""

    question = models.OneToOneField(
        PollQuestion, on_delete=models.CASCADE, related_name="_choice_input"
    )

    is_multiple = models.BooleanField(default=False)
    choice_type = models.CharField(
        choices=PollChoiceType.choices, default=PollChoiceType.DROPDOWN
    )

    # Foreign relations
    selections: models.QuerySet["PollQuestionAnswer"]
    options: models.QuerySet["ChoiceInputOption"]

    # Dyanmic properties
    @property
    def widget(self):
        return PollChoiceType(self.choice_type).label

    # Overrides
    class Meta:
        ordering = ["question__field", "-id"]

    def __str__(self):
        return f"{self.question} - {self.widget}"

    @property
    def poll(self):
        return self.question.field.poll


class ChoiceInputOption(ModelBase):
    """Option element inside select field."""

    input = models.ForeignKey(
        ChoiceInput, on_delete=models.CASCADE, related_name="options"
    )

    order = models.IntegerField(blank=True)
    label = models.CharField(max_length=100)
    value = models.CharField(blank=True, default="", max_length=100)
    image = models.ImageField(null=True, blank=True)
    is_default = models.BooleanField(default=False, blank=True)
    # is_other = models.BooleanField(default=False, blank=True)

    @property
    def html_name(self):
        return self.input.question.html_name

    @property
    def html_id(self):
        return f"option-{self.id}"

    # Overrides
    class Meta:
        ordering = ["order", "-id"]
        constraints = [
            models.UniqueConstraint(
                name="unique_default_option_per_choicefield",
                fields=["input", "is_default"],
                condition=models.Q(is_default=True),
            )
        ]

    def save(self, *args, **kwargs):
        if self.order is None:
            self.set_order()
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


class RangeInput(ModelBase):
    """Slider input."""

    question = models.OneToOneField(
        PollQuestion, on_delete=models.CASCADE, related_name="_range_input"
    )

    min_value = models.IntegerField(default=0)
    max_value = models.IntegerField(default=10)

    left_label = models.CharField(max_length=24, null=True, blank=True)
    right_label = models.CharField(max_length=24, null=True, blank=True)

    step = models.IntegerField(default=1)
    initial_value = models.IntegerField(default=0)
    unit = models.CharField(max_length=16, null=True, blank=True)

    @property
    def widget(self):
        return "Slide Range"


class UploadInput(ModelBase):
    """Upload button, file input."""

    question = models.OneToOneField(
        PollQuestion, on_delete=models.CASCADE, related_name="_upload_input"
    )

    # TODO: make enum
    file_types = ArrayField(
        base_field=models.CharField(max_length=32), blank=True, default=list
    )
    max_files = models.IntegerField(default=1)

    @property
    def widget(self):
        return "File Upload"


class NumberInput(ModelBase):
    """Number input, for numeric responses."""

    question = models.OneToOneField(
        PollQuestion, on_delete=models.CASCADE, related_name="_number_input"
    )

    min_value = models.FloatField(default=0.0)
    max_value = models.FloatField(default=10.0)

    unit = models.CharField(max_length=16, null=True, blank=True)

    decimal_places = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(0)]
    )

    @property
    def widget(self):
        return "Number Input"


class PollSubmission(ModelBase):
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
    @property
    def is_valid(self):
        # Is valid if no error and no answers have errors
        return (
            self.error is None and not self.answers.filter(error__isnull=True).exists()
        )


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


class PollQuestionAnswer(ModelBase):
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

    # # Only one other option is allowed for a question
    # other_option_value = models.CharField(null=True, blank=True)

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
        return (
            self.text_value
            or self.number_value
            or list(self.options_value.values_list("value", flat=True))
        )

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
