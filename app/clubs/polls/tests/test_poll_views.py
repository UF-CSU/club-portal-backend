from django.urls import reverse

from clubs.polls.models import (
    ChoiceInput,
    Poll,
    PollField,
    PollMarkup,
    PollQuestion,
    RangeInput,
    TextInput,
    UploadInput,
)
from core.abstracts.tests import AuthViewsTestsBase
from lib.faker import fake

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
                    "order": 4,
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
                    "order": 5,
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
                    "order": 6,
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
                    "order": 7,
                    "field_type": "page_break",
                },
                {
                    "order": 8,
                    "field_type": "markup",
                    "markup": {
                        "content": "# Hello World",
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
        self.assertEqual(PollQuestion.objects.count(), 7)
        self.assertEqual(TextInput.objects.count(), 3)
        self.assertEqual(ChoiceInput.objects.count(), 2)
        self.assertEqual(RangeInput.objects.count(), 1)
        self.assertEqual(UploadInput.objects.count(), 1)
        self.assertEqual(PollMarkup.objects.count(), 1)
