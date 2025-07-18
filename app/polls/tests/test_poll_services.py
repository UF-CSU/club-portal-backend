from core.abstracts.tests import TestsBase
from polls.models import PollTemplate
from polls.services import PollTemplateService


class PollTemplateServiceTests(TestsBase):
    """Unit tests for the poll template service."""

    def setUp(self):
        super().setUp()

        self.tpl = PollTemplate.objects.create(
            poll_name="Example Poll", template_name="Test Template"
        )
        self.service = PollTemplateService(self.tpl)

    # def test_create_poll(self):
    #     """Should create new poll from template."""

    #     # Setup fields
    #     f1 = PollField.objects.create(poll=self.tpl, order=1)
    #     f2 = PollField.objects.create(poll=self.tpl, order=2)

    #     expected_q1 = PollQuestion.objects.create(
    #         field=f1,
    #         label=fake.sentence(),
    #         input_type=PollInputType.TEXT,
    #         create_input=True,
    #     )
    #     expected_q2 = PollQuestion.objects.create(
    #         field=f2,
    #         label=fake.sentence(),
    #         input_type=PollInputType.TEXT,
    #         create_input=True,
    #     )

    #     # Generate poll
    #     poll = self.service.create_poll()
    #     self.assertIsNotNone(poll)
    #     self.assertEqual(poll.fields.count(), 2)
    #     self.assertEqual(PollField.objects.count(), 4)

    #     self.assertEqual(poll.fields.get(order=1).question.label, expected_q1.label)
    #     self.assertEqual(poll.fields.get(order=2).question.label, expected_q2.label)
