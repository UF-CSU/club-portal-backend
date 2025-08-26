from django.urls import reverse

from clubs.tests.utils import create_test_club
from core.abstracts.tests import PrivateApiTestsBase
from lib.faker import fake
from polls.models import (
    ChoiceInput,
    ChoiceInputOption,
    EmailInput,
    NumberInput,
    Poll,
    PollField,
    PollMarkup,
    PollQuestion,
    PollStatusType,
    ScaleInput,
    TextInput,
    UploadInput,
)
from polls.tests.utils import create_test_poll

POLLS_URL = reverse("api-polls:poll-list")


def polls_detail_url(id: int):
    return reverse("api-polls:poll-detail", args=[id])


def pollsubmission_list_url(poll_id: int):
    return reverse("api-polls:pollsubmission-list", kwargs={"poll_id": poll_id})


def pollfield_list_url(poll_id: int):
    return reverse("api-polls:pollfield-list", args=[poll_id])


def pollfield_detail_url(poll_id: int, pollfield_id: int):
    return reverse("api-polls:pollfield-detail", args=[poll_id, pollfield_id])


def polloption_list_url(poll_id: int, pollfield_id: int):
    return reverse("api-polls:pollchoiceoption-list", args=[poll_id, pollfield_id])


def polloption_detail_url(poll_id: int, pollfield_id: int, id: int):
    return reverse(
        "api-polls:pollchoiceoption-detail", args=[poll_id, pollfield_id, id]
    )


class PollViewAuthTests(PrivateApiTestsBase):
    """Test managing polls via REST api and views."""

    def setUp(self):
        super().setUp()

        self.club = create_test_club()

    def test_create_poll(self):
        """Should create poll via api."""

        payload = {
            "name": fake.title(),
            "description": fake.paragraph(),
            "club": {"id": self.club.id},
        }
        fields_payload = [
            {
                "order": 0,
                "field_type": "question",
                "question": {
                    "label": "Example short text question?",
                    "description": fake.paragraph(),
                    "input_type": "text",
                    "text_input": {
                        "text_type": "short",
                        "min_length": 5,
                        "max_length": 15,
                    },
                },
            },
            {
                "order": 1,
                "field_type": "question",
                "question": {
                    "label": "Example long text question?",
                    "description": fake.paragraph(),
                    "input_type": "text",
                    "text_input": {
                        "text_type": "long",
                        "min_length": 5,
                        "max_length": 500,
                    },
                },
            },
            {
                "order": 2,
                "field_type": "question",
                "question": {
                    "label": "Example rich text question?",
                    "description": fake.paragraph(),
                    "input_type": "text",
                    "text_input": {
                        "text_type": "rich",
                        "min_length": 5,
                        "max_length": 500,
                    },
                },
            },
            {
                "order": 3,
                "field_type": "question",
                "question": {
                    "label": "Example single choice question?",
                    "description": fake.paragraph(),
                    "input_type": "choice",
                    "choice_input": {
                        "multiple": False,
                        "single_choice_type": "select",
                        "options": [
                            {
                                "order": 0,
                                "label": "Option 1",
                            },
                            {
                                "order": 1,
                                "label": "Option 2",
                                "value": "option2",
                            },
                        ],
                    },
                },
            },
            {
                "order": 4,
                "field_type": "question",
                "question": {
                    "label": "Example single choice question?",
                    "description": fake.paragraph(),
                    "input_type": "choice",
                    "choice_input": {
                        "multiple": False,
                        "single_choice_type": "radio",
                        "options": [
                            {
                                "order": 0,
                                "label": "Option 1",
                            },
                            {
                                "order": 1,
                                "label": "Option 2",
                                "value": "option2",
                            },
                        ],
                    },
                },
            },
            {
                "order": 5,
                "field_type": "question",
                "question": {
                    "label": "Example choice question?",
                    "description": fake.paragraph(),
                    "input_type": "choice",
                    "choice_input": {
                        "multiple": True,
                        "multiple_choice_type": "checkbox",
                        "options": [
                            {
                                "order": 0,
                                "label": "Option 1",
                            },
                            {
                                "order": 1,
                                "label": "Option 2",
                                "value": "option2",
                            },
                        ],
                    },
                },
            },
            {
                "order": 6,
                "field_type": "question",
                "question": {
                    "label": "Example choice question?",
                    "description": fake.paragraph(),
                    "input_type": "choice",
                    "choice_input": {
                        "multiple": True,
                        "multiple_choice_type": "select",
                        "options": [
                            {
                                "order": 0,
                                "label": "Option 1",
                            },
                            {
                                "order": 1,
                                "label": "Option 2",
                                "value": "option2",
                            },
                        ],
                    },
                },
            },
            {
                "order": 7,
                "field_type": "question",
                "question": {
                    "label": "Example scale question?",
                    "description": fake.paragraph(),
                    "input_type": "scale",
                    "scale_input": {
                        "max_value": 10,
                        "initial_value": 5,
                    },
                },
            },
            {
                "order": 8,
                "field_type": "question",
                "question": {
                    "label": "Example upload question?",
                    "description": fake.paragraph(),
                    "input_type": "upload",
                    "upload_input": {
                        "file_types": [".pdf", ".docx"],
                        "max_files": 1,
                    },
                },
            },
            {
                "order": 9,
                "field_type": "page_break",
            },
            {
                "order": 10,
                "field_type": "markup",
                "markup": {
                    "content": "# Hello World",
                },
            },
            {
                "order": 11,
                "field_type": "question",
                "question": {
                    "label": "Example number question?",
                    "description": fake.paragraph(),
                    "input_type": "number",
                    "number_input": {
                        "min_value": 1,
                        "max_value": 5,
                        "decimal_places": 3,
                    },
                },
            },
        ]

        self.assertEqual(Poll.objects.count(), 0)

        url = POLLS_URL
        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Poll.objects.count(), 1)
        poll = Poll.objects.first()
        initial_fields_count = poll.fields.count()
        initial_question_count = poll.questions.count()

        field_url = pollfield_list_url(poll.pk)
        for field in fields_payload:
            res = self.client.post(field_url, field, format="json")
            self.assertResCreated(res)

        self.assertEqual(
            PollField.objects.count(), len(fields_payload) + initial_fields_count
        )
        self.assertEqual(PollQuestion.objects.count(), initial_question_count + 10)
        self.assertEqual(EmailInput.objects.count(), 1)  # Default email field
        self.assertEqual(TextInput.objects.count(), 3)
        self.assertEqual(ChoiceInput.objects.count(), 4)
        self.assertEqual(ScaleInput.objects.count(), 1)
        self.assertEqual(UploadInput.objects.count(), 1)
        self.assertEqual(PollMarkup.objects.count(), 1)
        self.assertEqual(NumberInput.objects.count(), 1)

    def test_update_poll(self):
        """Should update poll via api."""

        poll = create_test_poll(club=self.club)
        self.assertEqual(Poll.objects.count(), 1)

        payload = {
            "name": "Blake's Poll",
            "description": "This is a description for Blake's Poll.",
        }

        url = polls_detail_url(poll.pk)

        res = self.client.patch(url, data=payload, format="json")
        self.assertEqual(res.status_code, 200, res.content)

        poll.refresh_from_db()
        self.assertEqual(poll.name, payload["name"])
        self.assertEqual(poll.description, payload["description"])

    def test_update_poll_fields(self):
        """Should update poll via api."""

        poll = create_test_poll(club=self.club)
        self.assertEqual(Poll.objects.count(), 1)
        initial_field_count = poll.fields.count()
        initial_question_count = poll.questions.count()

        payload = {
            "order": 0,
            "field_type": "question",
            "question": {
                "label": "Updated question?",
                "description": fake.paragraph(),
                "input_type": "text",
                "text_input": {
                    "text_type": "short",
                    "min_length": 5,
                    "max_length": 15,
                },
            },
        }

        url = pollfield_list_url(poll.pk)

        res = self.client.post(url, data=payload, format="json")
        self.assertResCreated(res)

        poll.refresh_from_db()
        self.assertEqual(poll.fields.count(), initial_field_count + 1)
        self.assertEqual(poll.fields.first().field_type, "question")
        self.assertEqual(poll.fields.first().question.label, "Updated question?")

        update_field_payload = {
            "order": 0,
            "field_type": "question",
            "question": {
                "label": "Updated question again?",
                "description": fake.paragraph(),
                "input_type": "text",
                "text_input": {
                    "text_type": "short",
                    "min_length": 5,
                    "max_length": 15,
                },
            },
        }
        update_field_url = pollfield_detail_url(poll.pk, poll.fields.first().pk)

        update_field_res = self.client.patch(
            update_field_url, data=update_field_payload, format="json"
        )
        self.assertResOk(update_field_res)
        self.assertEqual(PollQuestion.objects.count(), initial_question_count + 1)

        add_field_payload = {
            "order": 1,
            "field_type": "question",
            "question": {
                "label": "Second question?",
                "description": fake.paragraph(),
                "input_type": "text",
                "text_input": {
                    "text_type": "short",
                    "min_length": 5,
                    "max_length": 15,
                },
            },
        }
        add_field_url = pollfield_list_url(poll.pk)
        add_field_res = self.client.post(
            add_field_url, add_field_payload, format="json"
        )
        self.assertResCreated(add_field_res)

        poll.refresh_from_db()
        self.assertEqual(poll.fields.count(), initial_field_count + 2)
        self.assertEqual(poll.fields.first().field_type, "question")
        self.assertEqual(poll.fields.first().question.label, "Updated question again?")
        self.assertEqual(poll.fields.last().field_type, "question")
        self.assertEqual(poll.fields.last().question.label, "Second question?")

    def test_update_choice_options(self):
        """Should be able to update the options for a choice field."""

        # Create initial poll and choice field
        poll = create_test_poll(club=self.club)

        payload = {
            "field_type": "question",
            "question": {
                "label": "Updated question?",
                "description": fake.paragraph(),
                "input_type": "choice",
                "choice_input": {
                    "is_multiple": True,
                    "multiple_choice_type": "select",
                    "options": [
                        {
                            "label": "Option 1",
                        },
                        {
                            "label": "Option 2",
                        },
                    ],
                },
            },
        }

        url = pollfield_list_url(poll.pk)

        res = self.client.post(url, data=payload)
        self.assertResCreated(res)

        # Add field to another poll
        poll2 = create_test_poll(club=self.club)
        url = pollfield_list_url(poll2.pk)
        res = self.client.post(url, data=payload)
        self.assertResCreated(res)

        # Get options
        field = poll.fields.last()
        self.assertIsNotNone(field)
        url = polloption_list_url(poll.id, field.id)

        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()
        self.assertLength(data, 2)

        # Add option
        payload = {"label": "Option 3", "value": "three"}
        res = self.client.post(url, payload)
        self.assertResCreated(res)
        self.assertEqual(field.question.choice_input.options.count(), 3)

        # Update option
        choice = ChoiceInputOption.objects.get(label="Option 3")
        url = polloption_detail_url(poll.id, field.id, choice.id)
        payload = {"label": "Option 03 updated"}
        res = self.client.patch(url, payload)
        self.assertResOk(res)

        choice.refresh_from_db()
        self.assertEqual(choice.label, "Option 03 updated")

        # Remove option
        res = self.client.delete(url)
        self.assertResNoContent(res)
        self.assertFalse(ChoiceInputOption.objects.filter(id=choice.id).exists())

    def test_delete_poll(self):
        """Should delete poll via api."""

        poll = create_test_poll(club=self.club)
        self.assertEqual(Poll.objects.count(), 1)

        url = polls_detail_url(poll.pk)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204, res.content)

        self.assertEqual(Poll.objects.count(), 0)

    def test_submission_poll(self):
        """Should submit poll via api."""

        # Create a poll with actual fields that match the submission payload
        poll = create_test_poll(club=self.club, status=PollStatusType.OPEN)

        # Create a poll field with a text question to match the submission
        poll_field = PollField.objects.create(poll=poll, field_type="question", order=0)

        poll_question = PollQuestion.objects.create(
            field=poll_field,
            label="Example short text question?",
            input_type="text",
            is_required=True,
        )

        TextInput.objects.create(
            question=poll_question, text_type="short", min_length=5, max_length=50
        )

        self.assertEqual(poll.submissions.count(), 0)

        payload = {
            "answers": [
                {
                    "question": poll_question.pk,
                    "text_value": "This is a short answer.",
                }
            ]
        }

        url = pollsubmission_list_url(poll.pk)

        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)

        poll.refresh_from_db()
        self.assertEqual(poll.submissions.count(), 1)

        # Verify the submission was created correctly
        submission = poll.submissions.first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.poll, poll)
        self.assertEqual(
            submission.user, self.user
        )  # Assuming AuthViewsTestsBase sets self.user

        # Verify the submission data contains the correct answer
        self.assertEqual(submission.answers.count(), 1)
        self.assertEqual(
            submission.answers.first().text_value, "This is a short answer."
        )

    def test_submission_poll_multiple_questions(self):
        """Should submit poll with multiple question types via api."""

        # Create a poll with multiple field types
        poll = create_test_poll(club=self.club, status=PollStatusType.OPEN)

        # Create text field
        text_field = PollField.objects.create(poll=poll, field_type="question", order=0)

        text_question = PollQuestion.objects.create(
            field=text_field,
            label="What is your name?",
            input_type="text",
            is_required=True,
        )

        TextInput.objects.create(
            question=text_question, text_type="short", min_length=1, max_length=100
        )

        # Create choice field
        choice_field = PollField.objects.create(
            poll=poll, field_type="question", order=1
        )

        choice_question = PollQuestion.objects.create(
            field=choice_field,
            label="What is your favorite color?",
            input_type="choice",
            is_required=True,
        )

        # This would be rendered as a radio field
        choice_input = ChoiceInput.objects.create(
            question=choice_question, is_multiple=False, choice_type="select"
        )

        ChoiceInputOption.objects.create(
            input=choice_input, order=0, label="Red", value="red"
        )
        ChoiceInputOption.objects.create(
            input=choice_input, order=1, label="Blue", value="blue"
        )

        # Create number field
        number_field = PollField.objects.create(
            poll=poll, field_type="question", order=2
        )

        number_question = PollQuestion.objects.create(
            field=number_field,
            label="Rate from 1 to 10",
            input_type="number",
            is_required=False,
        )

        NumberInput.objects.create(question=number_question, min_value=1, max_value=10)

        self.assertEqual(poll.submissions.count(), 0)

        payload = {
            "answers": [
                {
                    "question": text_question.pk,
                    "text_value": "John Doe",
                },
                {
                    "question": choice_question.pk,
                    # Multi is false, so > 1 would throw error
                    "options_value": ["blue"],
                },
                {
                    "question": number_question.id,
                    "number_value": 8.0,
                },
            ]
        }

        url = pollsubmission_list_url(poll.pk)

        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)

        poll.refresh_from_db()
        self.assertEqual(poll.submissions.count(), 1)

        # Verify the submission was created correctly
        submission = poll.submissions.first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.poll, poll)
        self.assertEqual(submission.user, self.user)

        # Verify the submission data contains all answers
        self.assertEqual(submission.answers.count(), 3)

        # Text answer
        self.assertEqual(
            submission.answers.get(question__id=text_question.pk).text_value, "John Doe"
        )

        # Choice answer
        self.assertEqual(
            submission.answers.get(question__id=number_question.pk).number_value, 8.0
        )

        # Number answer
        self.assertEqual(
            submission.answers.get(question__id=choice_question.pk)
            .options_value.all()
            .count(),
            1,
        )
        self.assertEqual(
            submission.answers.get(question__id=choice_question.pk)
            .options_value.first()
            .value,
            "blue",
        )

    # def test_submission_poll_validation_errors(self):
    #     """Should validate poll submission and return errors for invalid data."""

    #     # Create a poll with a required text field
    #     poll = Poll.objects.create(
    #         name=fake.title(),
    #         description=fake.paragraph(),
    #     )

    #     text_field = PollField.objects.create(poll=poll, field_type="question", order=0)

    #     text_question = PollQuestion.objects.create(
    #         field=text_field,
    #         label="Required question",
    #         input_type="text",
    #         required=True,
    #     )

    #     TextInput.objects.create(
    #         question=text_question, text_type="short", min_length=10, max_length=100
    #     )

    #     # Test with missing answer for required field
    #     payload = {"answers": []}

    #     url = pollsubmissions_list_url(poll.pk)

    #     res = self.client.post(url, data=payload, format="json")
    #     self.assertEqual(res.status_code, 400, res.content)
    #     self.assertEqual(poll.submissions.count(), 0)

    #     # Test with answer that's too short
    #     payload = {
    #         "answers": [
    #             {
    #                 "question": text_question.pk,
    #                 "text_value": "short",
    #             }
    #         ]
    #     }

    #     res = self.client.post(url, data=payload, format="json")
    #     # self.assertEqual(res.status_code, 400, res.content)
    #     self.assertResCreated(res)

    #     data = res.json()
    #     self.assertFalse(data["answers"][0]["is_valid"])
    #     self.assertEqual(poll.submissions.count(), 1)
    #     self.assertFalse(poll.submissions.first().is_valid)
    #     self.assertIsNotNone(poll.submissions.first().error)
