from clubs.tests.utils import create_test_club, create_test_clubfile
from core.abstracts.tests import (
    APIClientWrapper,
    PrivateApiTestsBase,
    PublicApiTestsBase,
)
from django.utils import timezone
from users.tests.utils import create_test_user

from polls.models import (
    CheckboxInput,
    ChoiceInput,
    ChoiceInputOption,
    DateInput,
    EmailInput,
    NumberInput,
    PhoneInput,
    PollField,
    PollQuestion,
    PollQuestionAnswer,
    PollSubmission,
    ScaleInput,
    TextInput,
    TimeInput,
    UploadInput,
    UrlInput,
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
        poll for an authenticated user part of and with editor permissions for a club"""

        poll = create_test_poll(open_at=timezone.now())
        url = pollanalytics_url(poll.pk)

        res = self.client.get(url)
        self.assertResForbidden(res)

        open_at = timezone.now()
        close_at = timezone.now() + timezone.timedelta(hours=2)
        c1 = create_test_club(admins=[self.user])
        p1 = create_test_poll(
            club=c1,
            open_at=open_at,
            close_at=close_at,
        )

        user2 = create_test_user()
        user3 = create_test_user()

        recurring = create_test_poll(club=c1, open_at=timezone.now())
        PollSubmission.objects.create(poll=recurring, user=self.user)

        ps1 = PollSubmission.objects.create(poll=p1, user=self.user)
        ps2 = PollSubmission.objects.create(poll=p1, user=user2)
        ps3 = PollSubmission.objects.create(poll=p1, user=user3)

        pf1 = PollField.objects.create(poll=p1)
        pq_text = PollQuestion.objects.create(
            field=pf1, label="Text", input_type="text"
        )

        TextInput.objects.create(question=pq_text, min_length=1, max_length=200)

        PollQuestionAnswer.objects.create(
            question=pq_text, submission=ps1, text_value="A few words."
        )
        PollQuestionAnswer.objects.create(
            question=pq_text,
            submission=ps2,
            text_value="A few words A few words A few words.",
        )
        PollQuestionAnswer.objects.create(
            question=pq_text,
            submission=ps3,
            text_value="A few words A few words A few words A few words A few words A few words.",
        )

        pf3 = PollField.objects.create(poll=p1)
        pq_url = PollQuestion.objects.create(field=pf3, label="Url", input_type="url")
        UrlInput.objects.create(question=pq_url)
        PollQuestionAnswer.objects.create(
            question=pq_url,
            submission=ps1,
            text_value="https://api.example.com/v1/users?id=42",
        )
        PollQuestionAnswer.objects.create(
            question=pq_url,
            submission=ps2,
            text_value="https://api.example.com/v2/orders?status=active",
        )
        PollQuestionAnswer.objects.create(
            question=pq_url,
            submission=ps3,
            text_value="https://data.example.com/export/report.csv",
        )

        pf4 = PollField.objects.create(poll=p1)
        pq_email = PollQuestion.objects.create(
            field=pf4, label="Email", input_type="email"
        )
        EmailInput.objects.create(question=pq_email, min_length=1, max_length=200)
        PollQuestionAnswer.objects.create(
            question=pq_email, submission=ps1, text_value="first@example.com"
        )
        PollQuestionAnswer.objects.create(
            question=pq_email, submission=ps2, text_value="second@example.com"
        )
        PollQuestionAnswer.objects.create(
            question=pq_email, submission=ps3, text_value="third@test.org"
        )

        pf5 = PollField.objects.create(poll=p1)
        pq_scale = PollQuestion.objects.create(
            field=pf5, label="Scale", input_type="scale"
        )
        ScaleInput.objects.create(question=pq_scale, max_value=10, initial_value=1)
        PollQuestionAnswer.objects.create(
            question=pq_scale, submission=ps1, number_value=2
        )
        PollQuestionAnswer.objects.create(
            question=pq_scale, submission=ps2, number_value=4
        )
        PollQuestionAnswer.objects.create(
            question=pq_scale, submission=ps3, number_value=6
        )

        pf5b = PollField.objects.create(poll=p1)
        pq_scale_large = PollQuestion.objects.create(
            field=pf5b, label="Scale Large", input_type="scale"
        )
        ScaleInput.objects.create(
            question=pq_scale_large, max_value=10, initial_value=7
        )
        PollQuestionAnswer.objects.create(
            question=pq_scale_large, submission=ps1, number_value=7
        )
        PollQuestionAnswer.objects.create(
            question=pq_scale_large, submission=ps2, number_value=8
        )
        PollQuestionAnswer.objects.create(
            question=pq_scale_large, submission=ps3, number_value=9
        )

        pf6 = PollField.objects.create(poll=p1)
        pq_upload = PollQuestion.objects.create(
            field=pf6, label="Upload", input_type="upload"
        )
        UploadInput.objects.create(question=pq_upload)
        file1 = create_test_clubfile(c1)
        file2 = create_test_clubfile(c1)
        file3 = create_test_clubfile(c1)
        PollQuestionAnswer.objects.create(
            question=pq_upload, submission=ps1, file_value=file1
        )
        PollQuestionAnswer.objects.create(
            question=pq_upload, submission=ps2, file_value=file2
        )
        PollQuestionAnswer.objects.create(
            question=pq_upload, submission=ps3, file_value=file3
        )

        pf7 = PollField.objects.create(poll=p1)
        pq_number = PollQuestion.objects.create(
            field=pf7, label="Number", input_type="number"
        )
        NumberInput.objects.create(question=pq_number, min_value=0, max_value=100)
        PollQuestionAnswer.objects.create(
            question=pq_number, submission=ps1, number_value=1
        )
        PollQuestionAnswer.objects.create(
            question=pq_number, submission=ps2, number_value=2
        )
        PollQuestionAnswer.objects.create(
            question=pq_number, submission=ps3, number_value=3
        )

        pf7b = PollField.objects.create(poll=p1)
        pq_number_large = PollQuestion.objects.create(
            field=pf7b, label="Number Large", input_type="number"
        )
        NumberInput.objects.create(
            question=pq_number_large, min_value=0, max_value=10000
        )
        PollQuestionAnswer.objects.create(
            question=pq_number_large, submission=ps1, number_value=1000
        )
        PollQuestionAnswer.objects.create(
            question=pq_number_large, submission=ps2, number_value=2000
        )
        PollQuestionAnswer.objects.create(
            question=pq_number_large, submission=ps3, number_value=3000
        )

        pf8 = PollField.objects.create(poll=p1)
        pq_phone = PollQuestion.objects.create(
            field=pf8, label="Phone", input_type="phone"
        )
        PhoneInput.objects.create(question=pq_phone)
        PollQuestionAnswer.objects.create(
            question=pq_phone, submission=ps1, text_value="123-555-0001"
        )
        PollQuestionAnswer.objects.create(
            question=pq_phone, submission=ps2, text_value="123-555-0002"
        )
        PollQuestionAnswer.objects.create(
            question=pq_phone, submission=ps3, text_value="917-555-0003"
        )

        pf9 = PollField.objects.create(poll=p1)
        pq_date = PollQuestion.objects.create(
            field=pf9, label="Date", input_type="date"
        )
        DateInput.objects.create(question=pq_date)
        PollQuestionAnswer.objects.create(
            question=pq_date, submission=ps1, text_value="2026-01-25"
        )
        PollQuestionAnswer.objects.create(
            question=pq_date, submission=ps2, text_value="2026-01-25"
        )
        PollQuestionAnswer.objects.create(
            question=pq_date, submission=ps3, text_value="2026-01-26"
        )

        pf10 = PollField.objects.create(poll=p1)
        pq_time = PollQuestion.objects.create(
            field=pf10, label="Time", input_type="time"
        )
        TimeInput.objects.create(question=pq_time)
        PollQuestionAnswer.objects.create(
            question=pq_time, submission=ps1, text_value="17:59"
        )
        PollQuestionAnswer.objects.create(
            question=pq_time, submission=ps2, text_value="17:59"
        )
        PollQuestionAnswer.objects.create(
            question=pq_time, submission=ps3, text_value="18:00"
        )

        pf11 = PollField.objects.create(poll=p1)
        pq_choice = PollQuestion.objects.create(
            field=pf11, label="Choice", input_type="choice"
        )
        ci = ChoiceInput.objects.create(question=pq_choice)
        option_1 = ChoiceInputOption.objects.create(input=ci, label="Option 1")
        option_2 = ChoiceInputOption.objects.create(input=ci, label="Option 2")
        option_3 = ChoiceInputOption.objects.create(input=ci, label="Option 3")
        PollQuestionAnswer.objects.create(
            question=pq_choice, submission=ps1, options_value=[option_1, option_2]
        )
        PollQuestionAnswer.objects.create(
            question=pq_choice, submission=ps2, options_value=[option_2]
        )
        PollQuestionAnswer.objects.create(
            question=pq_choice, submission=ps3, options_value=[option_3]
        )

        pf2 = PollField.objects.create(poll=p1)
        pq_checkbox = PollQuestion.objects.create(
            field=pf2, label="Checkbox", input_type="checkbox"
        )
        CheckboxInput.objects.create(question=pq_checkbox)
        PollQuestionAnswer.objects.create(
            question=pq_checkbox, submission=ps1, boolean_value=False
        )
        PollQuestionAnswer.objects.create(
            question=pq_checkbox, submission=ps2, boolean_value=True
        )
        PollQuestionAnswer.objects.create(
            question=pq_checkbox, submission=ps3, boolean_value=True
        )

        url = pollanalytics_url(p1.pk)
        res = self.client.get(url)
        self.assertResOk(res)
        analytics_data = res.json()

        self.assertEqual(
            open_at.isoformat().replace("+00:00", "Z"),
            analytics_data["open_at"],
        )
        self.assertEqual(
            close_at.isoformat().replace("+00:00", "Z"),
            analytics_data["close_at"],
        )
        self.assertEqual(p1.pk, analytics_data["id"])
        self.assertEqual(3, analytics_data["total_submissions"])
        self.assertEqual(3, analytics_data["total_users"])
        self.assertEqual(2, analytics_data["total_guest_users"])
        self.assertEqual(1, analytics_data["total_recurring_users"])
        self.assertEqual(2, analytics_data["total_submissions_change_from_average"])
        self.assertGreaterEqual(analytics_data["open_duration_seconds"], 0)
        heatmap_intervals = analytics_data["submissions_heatmap"]["intervals"]
        self.assertEqual(3, heatmap_intervals[min(heatmap_intervals)])

        def find_analytics_question(id: int):
            return [
                question
                for question in analytics_data["questions"]
                if question["id"] == id
            ][0]

        pq_text_data = find_analytics_question(pq_text.pk)
        self.assertEqual(pq_text.pk, pq_text_data["id"])
        self.assertEqual("text", pq_text_data["input_type"])
        self.assertEqual(3, pq_text_data["total_submissions"])
        self.assertEqual(3, len(pq_text_data["submissions"]))
        """
        Example:
        {'text_input': {'average_words': 10, 'max_words': 18, 'min_words': 3}
        """
        text_input_data = pq_text_data["analytics"]["text_input"]
        self.assertEqual(10, text_input_data["average_words"])
        self.assertEqual(18, text_input_data["max_words"])
        self.assertEqual(3, text_input_data["min_words"])

        pq_checkbox_data = find_analytics_question(pq_checkbox.pk)
        """
        Example:
        {'checkbox_input': {'total_true': 3}
        """
        checkbox_input_data = pq_checkbox_data["analytics"]["checkbox_input"]
        self.assertEqual(2, checkbox_input_data["total_true"])

        pq_url_data = find_analytics_question(pq_url.pk)
        """
        Example:
        {'url_input': {'total_unique_domains': 3}
        """
        url_input_data = pq_url_data["analytics"]["url_input"]
        self.assertEqual(2, url_input_data["total_unique_domains"])

        pq_email_data = find_analytics_question(pq_email.pk)
        """
        Example:
        {'email_input': {'email_domains': ['example.com', 'test.org']}}
        """
        email_input_data = pq_email_data["analytics"]["email_input"]
        self.assertCountEqual(
            ["example.com", "test.org"], email_input_data["email_domains"]
        )

        pq_scale_data = find_analytics_question(pq_scale.pk)
        """
        Example:
        {'scale_input': {'min_value': 2, 'max_value': 6, 'mean': 4, 'median': 4}}
        """
        scale_input_data = pq_scale_data["analytics"]["scale_input"]
        self.assertEqual(2, scale_input_data["min_value"])
        self.assertEqual(6, scale_input_data["max_value"])
        self.assertEqual(4, scale_input_data["mean"])
        self.assertEqual(4, scale_input_data["median"])
        pq_scale_large_data = find_analytics_question(pq_scale_large.pk)
        scale_large_input_data = pq_scale_large_data["analytics"]["scale_input"]
        self.assertEqual(7, scale_large_input_data["min_value"])
        self.assertEqual(9, scale_large_input_data["max_value"])
        self.assertEqual(8, scale_large_input_data["mean"])
        self.assertEqual(8, scale_large_input_data["median"])

        pq_upload_data = find_analytics_question(pq_upload.pk)
        """
        Example:
        {'upload_input': {'file_types': [{'file_type': 'png', 'count': 3}]}}
        """
        upload_input_data = pq_upload_data["analytics"]["upload_input"]
        self.assertEqual(1, len(upload_input_data["file_types"]))
        self.assertEqual(3, upload_input_data["file_types"][0]["count"])

        pq_number_data = find_analytics_question(pq_number.pk)
        """
        Example:
        {'number_input': {'min_value': 1, 'max_value': 3, 'mean': 2, 'median': 2}}
        """
        number_input_data = pq_number_data["analytics"]["number_input"]
        self.assertEqual(1, number_input_data["min_value"])
        self.assertEqual(3, number_input_data["max_value"])
        self.assertEqual(2, number_input_data["mean"])
        self.assertEqual(2, number_input_data["median"])
        pq_number_large_data = find_analytics_question(pq_number_large.pk)
        number_large_input_data = pq_number_large_data["analytics"]["number_input"]
        self.assertEqual(1000, number_large_input_data["min_value"])
        self.assertEqual(3000, number_large_input_data["max_value"])
        self.assertEqual(2000, number_large_input_data["mean"])
        self.assertEqual(2000, number_large_input_data["median"])

        pq_phone_data = find_analytics_question(pq_phone.pk)
        """
        Example:
        {'phone_input': {'area_codes': [{'area_code': '123', 'count': 2}]}}
        """
        phone_input_data = pq_phone_data["analytics"]["phone_input"]
        area_codes = {
            item["area_code"]: item["count"] for item in phone_input_data["area_codes"]
        }
        self.assertEqual(2, area_codes["123"])
        self.assertEqual(1, area_codes["917"])

        pq_date_data = find_analytics_question(pq_date.pk)
        """
        Example:
        {'date_input': {'dates': [{'date': '2026-01-25', 'count': 2}]}}
        """
        date_input_data = pq_date_data["analytics"]["date_input"]
        dates = {item["date"]: item["count"] for item in date_input_data["dates"]}
        self.assertEqual(2, dates["2026-01-25"])
        self.assertEqual(1, dates["2026-01-26"])

        pq_time_data = find_analytics_question(pq_time.pk)
        """
        Example:
        {'time_input': {'times': [{'time': '17:59', 'count': 2}]}}
        """
        time_input_data = pq_time_data["analytics"]["time_input"]
        times = {item["time"]: item["count"] for item in time_input_data["times"]}
        self.assertEqual(2, times["17:59"])
        self.assertEqual(1, times["18:00"])

        pq_choice_data = find_analytics_question(pq_choice.pk)
        """
        Example:
        {'option_input': {'options_submissions_count': [...]}}
        """
        option_input_data = pq_choice_data["analytics"]["option_input"]
        option_counts = {
            item["label"]: item["total_submissions"]
            for item in option_input_data["options_submissions_count"]
        }
        self.assertEqual(1, option_counts["Option 1"])
        self.assertEqual(2, option_counts["Option 2"])
        self.assertEqual(1, option_counts["Option 3"])
