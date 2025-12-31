from datetime import timedelta

from clubs.tests.utils import create_test_club
from core.abstracts.tests import (
    APIClientWrapper,
    PrivateApiTestsBase,
    PublicApiTestsBase,
)
from django.utils import timezone
from users.tests.utils import create_test_user

from polls.models import (
    ChoiceInput,
    ChoiceInputOption,
    PollField,
    PollInputType,
    PollQuestion,
    PollQuestionAnswer,
    PollSubmission,
)
from polls.tests.utils import (
    create_test_poll,
    pollanalytics_url,
)


class PollViewPublicTests(PublicApiTestsBase):
    """Tests denial of retrieval if a user is unauthenticated when accessing poll analytics"""

    def test_guest_get_poll_analytics(self):
        """Should deny guest from accessing poll analytics"""

        poll = create_test_poll()
        url = pollanalytics_url(poll.pk)

        res = self.client.get(url)
        self.assertResUnauthorized(res)


class PollAnalyticsPrivateTests(PrivateApiTestsBase):
    """Tests retrieval of analytics for polls when a user has the correct permissions"""

    def setUp(self):
        self.user = create_test_user()
        self.client = APIClientWrapper()
        self.client.force_authenticate(self.user)

    def test_get_poll_analytics(self):
        """Poll analytics view should correctly compile and return analytics for a
        poll for an authenticated user part with editor permissions for a club"""

        poll = create_test_poll()
        url = pollanalytics_url(poll.pk)

        res = self.client.get(url)
        self.assertResForbidden(res)

        c1 = create_test_club(admins=[self.user])
        p1 = create_test_poll(club=c1)

        url = pollanalytics_url(p1.pk)

        # Ensure submission_vs_time is correctly added to the response
        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()

        self.assertIn("submission_vs_time", data)
        self.assertListEqual(data["submission_vs_time"], [])

        # Submission time should be correctly ordered and count should be corresponding to submissions
        today = timezone.now()
        one_day = timedelta(days=1)
        yesterday = today - one_day

        ps1 = PollSubmission.objects.create(poll=p1, user=self.user)
        PollSubmission.objects.update_one(ps1.pk, created_at=yesterday)
        ps2 = PollSubmission.objects.create(poll=p1, user=self.user, created_at=today)
        ps3 = PollSubmission.objects.create(poll=p1, user=self.user, created_at=today)

        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()

        self.assertIn("submission_vs_time", data)
        self.assertLess(
            data["submission_vs_time"][0]["submission_date"],
            data["submission_vs_time"][1]["submission_date"],
        )
        self.assertEqual(
            data["submission_vs_time"][0]["count"],
            1,
        )
        self.assertEqual(
            data["submission_vs_time"][1]["count"],
            2,
        )

        # Test analytics for checkbox question types
        pf1 = PollField.objects.create(poll=p1, order=0)
        pq1 = PollQuestion.objects.create(
            field=pf1, label="Q1", input_type=PollInputType.CHECKBOX
        )
        PollQuestionAnswer.objects.create(
            question=pq1, submission=ps2, boolean_value=True
        )
        PollQuestionAnswer.objects.create(
            question=pq1, submission=ps3, boolean_value=False
        )

        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()

        self.assertIn("submission_vs_time", data)
        self.assertIn("answer_analytics", data)
        self.assertEqual(data["answer_analytics"][0]["order"], 0)
        self.assertEqual(data["answer_analytics"][0]["question"]["label"], "Q1")
        self.assertEqual(data["answer_analytics"][0]["count"], 2)
        self.assertEqual(data["answer_analytics"][0]["trues"], 1)
        self.assertEqual(data["answer_analytics"][0]["falses"], 1)

        # Tests analytics for choice question types
        pf2 = PollField.objects.create(poll=p1, order=1)
        pq2 = PollQuestion.objects.create(
            field=pf2, label="Q2", input_type=PollInputType.CHOICE
        )

        ci1 = ChoiceInput.objects.create(
            question=pq2, is_multiple=False, choice_type="select"
        )

        cio1 = ChoiceInputOption.objects.create(
            input=ci1, order=0, label="Red", value="red"
        )
        ChoiceInputOption.objects.create(
            input=ci1, order=2, label="Green", value="green"
        )
        cio2 = ChoiceInputOption.objects.create(
            input=ci1, order=1, label="Blue", value="blue"
        )

        PollQuestionAnswer.objects.create(
            question=pq2, submission=ps2, options_value=[cio1]
        )
        PollQuestionAnswer.objects.create(
            question=pq2, submission=ps3, options_value=[cio2]
        )
        PollQuestionAnswer.objects.create(
            question=pq2, submission=ps1, options_value=[cio2]
        )

        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()

        self.assertIn("submission_vs_time", data)
        self.assertIn("answer_analytics", data)
        self.assertIn("selections", data["answer_analytics"][2])
        self.assertIn("selection_counts", data["answer_analytics"][2])
        self.assertEqual(data["answer_analytics"][2]["order"], 1)
        self.assertEqual(data["answer_analytics"][2]["question"]["label"], "Q2")
        self.assertEqual(data["answer_analytics"][2]["count"], 3)
        self.assertEqual(data["answer_analytics"][2]["trues"], 0)
        self.assertEqual(data["answer_analytics"][2]["falses"], 0)
        self.assertEqual(
            data["answer_analytics"][2]["selections"], ["red", "blue", "green"]
        )
        self.assertEqual(data["answer_analytics"][2]["selection_counts"], [1, 2, 0])

        pf3 = PollField.objects.create(poll=p1, order=2)
        pq3 = PollQuestion.objects.create(
            field=pf3, label="Q3", input_type=PollInputType.CHOICE
        )

        ci2 = ChoiceInput.objects.create(
            question=pq3, is_multiple=True, choice_type="select"
        )

        cio3 = ChoiceInputOption.objects.create(
            input=ci2, order=2, label="Red", value="red"
        )
        cio4 = ChoiceInputOption.objects.create(
            input=ci2, order=1, label="Green", value="green"
        )
        cio5 = ChoiceInputOption.objects.create(
            input=ci2, order=0, label="Blue", value="blue"
        )

        PollQuestionAnswer.objects.create(
            question=pq3, submission=ps2, options_value=[cio4, cio3]
        )
        PollQuestionAnswer.objects.create(
            question=pq3, submission=ps3, options_value=[cio4, cio5]
        )
        PollQuestionAnswer.objects.create(
            question=pq3, submission=ps1, options_value=[cio3, cio5, cio4]
        )

        res = self.client.get(url)
        self.assertResOk(res)

        data = res.json()

        self.assertIn("submission_vs_time", data)
        self.assertIn("answer_analytics", data)
        self.assertIn("selections", data["answer_analytics"][3])
        self.assertIn("selection_counts", data["answer_analytics"][3])
        self.assertEqual(data["answer_analytics"][3]["order"], 2)
        self.assertEqual(data["answer_analytics"][3]["question"]["label"], "Q3")
        self.assertEqual(data["answer_analytics"][3]["count"], 3)
        self.assertEqual(data["answer_analytics"][3]["trues"], 0)
        self.assertEqual(data["answer_analytics"][3]["falses"], 0)
        self.assertEqual(
            data["answer_analytics"][3]["selections"], ["blue", "green", "red"]
        )
        self.assertEqual(data["answer_analytics"][3]["selection_counts"], [2, 3, 2])
