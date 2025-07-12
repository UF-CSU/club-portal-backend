from django.urls import reverse

from core.abstracts.tests import AuthViewsTestsBase
from lib.faker import fake
from polls.models import (
    ChoiceInput,
    ChoiceInputOption,
    Poll,
    PollField,
    PollMarkup,
    PollQuestion,
    RangeInput,
    TextInput,
    UploadInput,
    NumberInput,
)

POLLS_URL = reverse("api-clubpolls:polls-list")


class PollViewAuthTests(AuthViewsTestsBase):
    """Test managing polls via REST api and views."""

    def test_create_poll(self):
        """Should create poll via api."""

        payload = {
            "name": fake.title(),
            "description": fake.paragraph(),
            "fields": [
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
                        "label": "Example range question?",
                        "description": fake.paragraph(),
                        "input_type": "range",
                        "range_input": {
                            "min_value": 0,
                            "max_value": 100,
                            "initial_value": 50,
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
                            "file_types": ["pdf", "docx"],
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
            ],
        }

        self.assertEqual(Poll.objects.count(), 0)

        url = POLLS_URL
        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, 201, res.content)

        self.assertEqual(Poll.objects.count(), 1)
        self.assertEqual(PollField.objects.count(), len(payload["fields"]))
        self.assertEqual(PollQuestion.objects.count(), 10)
        self.assertEqual(TextInput.objects.count(), 3)
        self.assertEqual(ChoiceInput.objects.count(), 4)
        self.assertEqual(RangeInput.objects.count(), 1)
        self.assertEqual(UploadInput.objects.count(), 1)
        self.assertEqual(PollMarkup.objects.count(), 1)
        self.assertEqual(NumberInput.objects.count(), 1)

    def test_update_poll(self):
        """Should update poll via api."""

        poll = Poll.objects.create(
            name=fake.title(),
            description=fake.paragraph(),
        )

        self.assertEqual(Poll.objects.count(), 1)

        payload = {
            "name": "Blake's Poll",
            "description": "This is a description for Blake's Poll.",
        }

        url = POLLS_URL + f"{poll.id}/"

        res = self.client.patch(url, data=payload, format="json")
        self.assertEqual(res.status_code, 200, res.content)

        poll.refresh_from_db()
        self.assertEqual(poll.name, payload["name"])
        self.assertEqual(poll.description, payload["description"])

    def test_delete_poll(self):
        """Should delete poll via api."""

        poll = Poll.objects.create(
            name=fake.title(),
            description=fake.paragraph(),
        )

        self.assertEqual(Poll.objects.count(), 1)

        url = POLLS_URL + f"{poll.id}/"

        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204, res.content)

        self.assertEqual(Poll.objects.count(), 0)

    def test_submission_poll(self):
        """Should submit poll via api."""

        # Create a poll with actual fields that match the submission payload
        poll = Poll.objects.create(
            name=fake.title(),
            description=fake.paragraph(),
        )

        # Create a poll field with a text question to match the submission
        poll_field = PollField.objects.create(poll=poll, field_type="question", order=0)

        poll_question = PollQuestion.objects.create(
            field=poll_field,
            label="Example short text question?",
            input_type="text",
            required=True,
        )

        TextInput.objects.create(
            question=poll_question, text_type="short", min_length=5, max_length=50
        )

        self.assertEqual(poll.submissions.count(), 0)

        payload = {
            "answers": [
                {
                    "field": poll_field.id,
                    "text_input": {
                        "text_type": "short",
                        "value": "This is a short answer.",
                    },
                }
            ]
        }

        url = POLLS_URL + f"{poll.id}/submit/"

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
        self.assertIsNotNone(submission.data)
        self.assertIn("answers", submission.data)
        self.assertEqual(len(submission.data["answers"]), 1)

        answer = submission.data["answers"][0]
        self.assertEqual(answer["field"], poll_field.id)
        self.assertIn("text_input", answer)
        self.assertEqual(answer["text_input"]["text_type"], "short")
        self.assertEqual(answer["text_input"]["value"], "This is a short answer.")

    def test_submission_poll_multiple_questions(self):
        """Should submit poll with multiple question types via api."""

        # Create a poll with multiple field types
        poll = Poll.objects.create(
            name=fake.title(),
            description=fake.paragraph(),
        )

        # Create text field
        text_field = PollField.objects.create(poll=poll, field_type="question", order=0)

        text_question = PollQuestion.objects.create(
            field=text_field,
            label="What is your name?",
            input_type="text",
            required=True,
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
            required=True,
        )

        choice_input = ChoiceInput.objects.create(
            question=choice_question, multiple=False, single_choice_type="radio"
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
            required=False,
        )

        NumberInput.objects.create(
            question=number_question, min_value=1, max_value=10, decimal_places=0
        )

        self.assertEqual(poll.submissions.count(), 0)

        payload = {
            "answers": [
                {
                    "field": text_field.id,
                    "text_input": {
                        "text_type": "short",
                        "value": "John Doe",
                    },
                },
                {
                    "field": choice_field.id,
                    "choice_input": {
                        "value": "blue",
                    },
                },
                {
                    "field": number_field.id,
                    "number_input": {
                        "value": 8.0,
                    },
                },
            ]
        }

        url = POLLS_URL + f"{poll.id}/submit/"

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
        self.assertIsNotNone(submission.data)
        self.assertIn("answers", submission.data)
        self.assertEqual(len(submission.data["answers"]), 3)

        # Verify each answer type
        answers_by_field = {
            answer["field"]: answer for answer in submission.data["answers"]
        }

        # Text answer
        text_answer = answers_by_field[text_field.id]
        self.assertEqual(text_answer["text_input"]["value"], "John Doe")

        # Choice answer
        choice_answer = answers_by_field[choice_field.id]
        self.assertEqual(choice_answer["choice_input"]["value"], "blue")

        # Number answer
        number_answer = answers_by_field[number_field.id]
        self.assertEqual(number_answer["number_input"]["value"], 8.0)

    def test_submission_poll_validation_errors(self):
        """Should validate poll submission and return errors for invalid data."""

        # Create a poll with a required text field
        poll = Poll.objects.create(
            name=fake.title(),
            description=fake.paragraph(),
        )

        text_field = PollField.objects.create(poll=poll, field_type="question", order=0)

        text_question = PollQuestion.objects.create(
            field=text_field,
            label="Required question",
            input_type="text",
            required=True,
        )

        TextInput.objects.create(
            question=text_question, text_type="short", min_length=10, max_length=100
        )

        # Test with missing answer for required field
        payload = {"answers": []}

        url = POLLS_URL + f"{poll.id}/submit/"

        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(poll.submissions.count(), 0)

        # Test with answer that's too short
        payload = {
            "answers": [
                {
                    "field": text_field.id,
                    "text_input": {
                        "text_type": "short",
                        "value": "short",  # Less than min_length of 10
                    },
                }
            ]
        }

        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(poll.submissions.count(), 0)
