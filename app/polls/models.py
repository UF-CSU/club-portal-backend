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

"""

from typing import ClassVar, Optional

from django.core import exceptions
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.abstracts.models import ManagerBase, ModelBase
from events.models import Event, EventType
from users.models import User


class PollType(models.TextChoices):
    """Different types of polls."""

    STANDARD = "standard", _("Standard")
    TEMPLATE = "template", _("Template")


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

    SHORT = "short", _("Short Text Input")
    LONG = "long", _("Long Text Input")
    RICH = "rich", _("Rich Text Input")


class PollChoiceType(models.TextChoices):
    """Different ways of showing a choice field."""

    DROPDOWN = "select", _("Dropdown Select")
    SELECT = "radio", _("Input Select")


# class PollSingleChoiceType(models.TextChoices):
#     """Different ways of showing single choice fields."""

#     SELECT = "select", _("Single Dropdown Select")
#     RADIO = "radio", _("Single Radio Select")


# class PollMultiChoiceType(models.TextChoices):
#     """Different ways of showing multichoice fields."""

#     SELECT = "select", _("Multi Select Box")
#     CHECKBOX = "checkbox", _("Multi Checkbox Select")


class PollManager(ManagerBase["Poll"]):
    """Manage queries for polls."""

    def create(self, name: str, **kwargs):
        return super().create(name=name, **kwargs)


class Poll(ModelBase):
    """Custom form."""

    name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)
    poll_type = models.CharField(
        choices=PollType.choices, default=PollType.STANDARD, editable=False
    )

    # Foreign Relationships
    fields: models.QuerySet["PollField"]
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="_poll", blank=True, null=True)

    # Overrides
    objects: ClassVar[PollManager] = PollManager()

    def save(self, *args, **kwargs):
        if hasattr(self, "polltemplate"):
            self.poll_type = PollType.TEMPLATE

        return super().save(*args, **kwargs)

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
    order = models.IntegerField()

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
        ordering = ["order", "-id"]

    def __str__(self):
        return f"{self.poll} - {self.order}"

    def clean(self):
        """
        Validate data before it hits database.
        Sends Validation Error before database sends Integrety Error,
        has better UX.
        """

        # Check order field
        order_query = PollField.objects.filter(poll=self.poll, order=self.order)
        if order_query.count() > 1:
            raise exceptions.ValidationError(
                f"Multiple fields are set to order {self.order}."
            )

        return super().clean()

    def save(self, *args, **kwargs):
        if self.field_type is None:
            if self.question is not None:
                self.field_type = PollFieldType.QUESTION
            elif self.page_break is not None:
                self.field_type = PollFieldType.PAGE_BREAK
            elif self.markup is not None:
                self.field_type = PollFieldType.MARKUP

        return super().save(*args, **kwargs)


class PollMarkup(ModelBase):
    """Store markdown content for a poll."""

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
    required = models.BooleanField(default=False)

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

    # Dyanmic properties
    @property
    def widget(self):
        return PollChoiceType(self.choice_type).label

    # Overrides
    class Meta:
        ordering = ["question__field", "-id"]

    def __str__(self):
        return f"{self.question.field} - {self.widget}"


class ChoiceInputOption(ModelBase):
    """Option element inside select field."""

    input = models.ForeignKey(
        ChoiceInput, on_delete=models.CASCADE, related_name="options"
    )

    order = models.IntegerField()
    label = models.CharField(max_length=100)
    value = models.CharField(blank=True, default="", max_length=100)
    image = models.ImageField(null=True, blank=True)

    @property
    def html_name(self):
        return self.input.question.html_name

    @property
    def html_id(self):
        return f"option-{self.id}"

    # Overrides
    class Meta:
        ordering = ["order", "-id"]

    def clean(self):
        """Validate data before it hits database."""

        # Allow user to only provide label, value will sync
        if self.value is None or self.value.strip() == "":
            self.value = self.label

        return super().clean()


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

    # TODO: How to handle list of file types?
    file_types = models.CharField(default="any")
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

    # Foreign relations
    answers: models.QuerySet["PollQuestionAnswer"]

    # Overrides
    def __str__(self):
        return f"Submission from {self.user or 'anonymous'}"

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

    # Validation
    error = models.CharField(
        null=True, blank=True, help_text="Error message if input is not valid."
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
