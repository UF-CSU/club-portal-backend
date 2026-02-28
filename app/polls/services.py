import pandas as pd
import pytz
from app.settings import POLL_SUBMISSION_REDIRECT_URL
from core.abstracts.schedules import schedule_clocked_func
from core.abstracts.services import ServiceBase
from django.db import connection, models
from django.utils import timezone
from events.models import EventAttendance
from utils.db import dictfetchall
from utils.logging import print_error

from polls.models import (
    ChoiceInput,
    Poll,
    PollField,
    PollFieldType,
    PollInputType,
    PollMarkup,
    PollQuestion,
    PollQuestionAnswer,
    PollStatusType,
    PollSubmission,
    PollSubmissionLink,
    PollTemplate,
    PollUserFieldType,
    TextInput,
)
from polls.serializers import (
    PollAnalyticsSubmissionsHeatmapSerializer,
    PollSubmissionSerializer,
)


class PollTemplateService(ServiceBase[PollTemplate]):
    """Business logic for polls."""

    model = PollTemplate

    def _clone_input(self, question_tpl: PollQuestion, target_question: PollQuestion):
        """Clone question to poll."""

        match question_tpl.input_type:
            case PollInputType.TEXT:
                TextInput.objects.create(
                    question=target_question,
                    text_type=question_tpl.text_input.text_type,
                    min_length=question_tpl.text_input.min_length,
                    max_length=question_tpl.text_input.max_length,
                )
            case PollInputType.CHOICE:
                ChoiceInput.objects.create(
                    question=target_question,
                )

    def _clone_field(self, field_tpl: PollField, target_poll: Poll):
        """Clone field to poll."""

        # field = target_poll.add_field(field_type=field_tpl.field_type)
        # print(field)
        # Create new field directly instead of using add_field
        field = PollField.objects.create(
            poll=target_poll,
            field_type=field_tpl.field_type,
        )

        match field.field_type:
            case PollFieldType.QUESTION:
                q_tpl = field_tpl.question
                question = PollQuestion.objects.create(
                    field=field,
                    label=q_tpl.label,
                    input_type=q_tpl.input_type,
                    create_input=False,
                    description=q_tpl.description,
                )
                self._clone_input(q_tpl, question)
            case PollFieldType.MARKUP:
                PollMarkup.objects.create(field=field, content=field_tpl.markup.content)

        return field

    def create_poll(self, **kwargs) -> Poll:
        """Create a new poll from this one if it is a template."""

        # Create the poll without any auto-created fields
        poll = Poll.objects.create(
            name=self.obj.name, description=self.obj.description, **kwargs
        )

        # Get template fields ordered by their order field
        template_fields = self.obj.fields.all().order_by("order")

        # Clone each field
        for field_tpl in template_fields:
            self._clone_field(field_tpl, poll)

        # Refresh to get accurate field count
        poll.refresh_from_db()
        return poll


class PollService(ServiceBase[Poll]):
    """Business logic for polls."""

    model = Poll

    def _validate_submission(self, submission: PollSubmission, raise_exception=False):
        """Check if a poll submission is valid."""

        for _answer in submission.answers.all():
            pass

        return submission

    def _remove_task(self, field):
        task = getattr(self.obj, field)
        setattr(self.obj, field, None)
        task.delete()

    def _schedule_poll_open(self):
        """Maked a periodic task for opening the poll."""

        if self.obj.open_task is not None:
            self._remove_task("open_task")

        task = schedule_clocked_func(
            name=f"Set {self.obj.name} as open",
            due_at=self.obj.open_at,
            func=set_poll_status,
            kwargs={"poll_id": self.obj.id, "status": PollStatusType.OPEN},
        )
        self.obj.open_task = task

    def _schedule_poll_close(self):
        """Maked a periodic task for closing the poll."""

        if self.obj.close_task is not None:
            self._remove_task("close_task")

        task = schedule_clocked_func(
            name=f"Set {self.obj.name} as closed",
            due_at=self.obj.close_at,
            func=set_poll_status,
            kwargs={"poll_id": self.obj.id, "status": PollStatusType.CLOSED},
        )
        self.obj.close_task = task

    def sync_status_tasks(self):
        """
        Ensure the poll has periodic tasks if `open_at` and/or `close_at` are set.
        """

        poll = self.obj
        poll.refresh_from_db()

        has_open_at = poll.open_at is not None
        has_open_task = poll.open_task is not None
        has_close_at = poll.close_at is not None
        has_close_task = poll.close_task is not None

        # Sync open task
        if not has_open_at and has_open_task:
            self._remove_task("open_task")
        elif has_open_at and not has_open_task:
            self._schedule_poll_open()
        elif (
            has_open_at
            and has_open_task
            and poll.open_at != poll.open_task.clocked.clocked_time
        ):
            self._schedule_poll_open()

        # Sync close task
        if not has_close_at and has_close_task:
            self._remove_task("close_task")
        elif has_close_at and not has_close_task:
            self._schedule_poll_close()
        elif (
            has_close_at
            and has_close_task
            and poll.close_at != poll.close_task.clocked.clocked_time
        ):
            self._schedule_poll_close()

        poll.save()

    @staticmethod
    def get_submissions(poll_id: int):
        """Get all submissions for a poll."""
        submissions = (
            PollSubmission.objects.filter(poll_id=poll_id)
            .select_related("user", "user__profile")
            .prefetch_related(
                models.Prefetch(
                    "answers",
                    queryset=PollQuestionAnswer.objects.prefetch_related(
                        "options_value"
                    ),
                ),
                "user__verified_emails",
            )
        )
        serializer = PollSubmissionSerializer(submissions, many=True)
        return serializer.data

    def get_submissions_df(self, tzname=None) -> pd.DataFrame:
        """Convert submissions to pandas dataframe."""

        data = []
        tzname = tzname or "UTC"

        for submission in self.obj.submissions.all():
            try:
                row = {
                    "User ID": submission.user.id,
                    # "User Email": submission.user.email,
                    "User School Email": submission.user.profile.school_email,
                    "Submission Date": timezone.localtime(
                        submission.created_at, timezone=pytz.timezone(tzname)
                    ),
                    **{
                        answer.label: answer.value
                        for answer in submission.answers.all()
                    },
                }
            except Exception as e:
                row = {"User ID": submission.user.id}
                print_error()
                print(e)

            data.append(row)

        return pd.DataFrame(data)

    def create_question(self, label: str, input_type=PollInputType.TEXT, **kwargs):
        """Create new question, with associated field and input for poll."""

        poll = self.obj
        field = kwargs.pop(
            "field",
            PollField.objects.create(poll, field_type="question"),
        )
        payload = {
            "field": field,
            "label": label,
            "input_type": input_type,
            "create_input": True,
            **kwargs,
        }
        return PollQuestion.objects.create(**payload)

    def _update_user_fields_from_submission(self, submission: PollSubmission):
        """For each answer with a linked user field in submission, update user field."""

        answers = submission.answers.all()
        user = submission.user

        if not user:
            return

        for answer in answers:
            if answer.question.link_user_field is None:
                continue

            match answer.question.link_user_field:
                case PollUserFieldType.NAME:
                    user.profile.name = answer.value or user.profile.name
                    user.profile.save()
                case PollUserFieldType.PHONE:
                    user.profile.phone = answer.value or user.profile.phone
                    user.profile.save()
                case PollUserFieldType.MAJOR:
                    user.profile.major = answer.value or user.profile.major
                    user.profile.save()
                case PollUserFieldType.MINOR:
                    user.profile.minor = answer.value or user.profile.minor
                    user.profile.save()
                case PollUserFieldType.COLLEGE:
                    user.profile.college = answer.value or user.profile.college
                    user.profile.save()
                case PollUserFieldType.GRADUATION_YEAR:
                    user.profile.graduation_year = (
                        answer.value or user.profile.graduation_year
                    )
                    user.profile.save()

    def process_submission(self, submission: PollSubmission):
        """Run all actions for submission object."""

        assert submission.poll.pk == self.obj.pk, (
            f"Invalid submission, expected poll id {self.obj.pk} but found {submission.poll.id}."
        )

        self._validate_submission(submission)
        self._update_user_fields_from_submission(submission)

        if self.obj.event is not None:
            EventAttendance.objects.get_or_create(
                user=submission.user, event=self.obj.event
            )

        submission.refresh_from_db()
        return submission

    def create_submission_link(self):
        """Create link where users can fill out poll."""

        if self.obj.submission_link is not None:
            return

        url = POLL_SUBMISSION_REDIRECT_URL % {"id": self.obj.id}
        return PollSubmissionLink.objects.create(
            target_url=url, poll=self.obj, club=self.obj.club, create_qrcode=True
        )

    def sync_submission_link(self):
        """Remove and recreate submission links."""

        if self.obj.submission_link is not None:
            PollSubmissionLink.objects.filter(id=self.obj.submission_link.id).delete()

        self.create_submission_link()


def set_poll_status(poll_id: int, status: PollStatusType):
    """Set a poll as open."""

    poll = Poll.objects.get_by_id(poll_id)
    poll.status = status
    poll.save()


class PollAnalyticsService(ServiceBase[Poll]):
    """Business logic for poll analytics"""

    model = Poll

    def get_total_submissions(self) -> int:
        return self.obj.submissions_count

    def get_open_duration_seconds(self) -> int:
        return (timezone.now() - self.obj.open_at).total_seconds()

    def get_total_users(self) -> int:
        return (
            PollSubmission.objects.filter(poll__pk=self.obj.pk)
            .values("user")
            .distinct()
            .count()
        )

    def get_total_guest_users(self) -> int:
        query = f"""
                SELECT COUNT(*) AS total_guest_users FROM public.polls_pollsubmission
                WHERE public.polls_pollsubmission.poll_id = {self.obj.pk}
                AND user_id NOT IN (
                    SELECT DISTINCT user_id FROM public.clubs_clubmembership
                    JOIN public.polls_poll ON public.polls_poll.club_id = public.clubs_clubmembership.club_id
                    WHERE public.polls_poll.id = {self.obj.pk}
                );
                """
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

            return result[0]["total_guest_users"]

    def get_total_recurring_users(self) -> int:
        query = f"""
                SELECT COUNT(*) AS total_recurring_users
                FROM (
                    SELECT ps.user_id
                    FROM public.polls_pollsubmission ps
                    JOIN public.polls_poll p ON p.id = ps.poll_id
                    WHERE p.club_id = {self.obj.club.pk}
                    GROUP BY ps.user_id
                    HAVING COUNT(*) > 1
                ) _;
                """
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

            return result[0]["total_recurring_users"]

    def get_total_submissions_change_from_average(self) -> float:
        query = f"""
                WITH values AS (
                    SELECT
                        (
                            SELECT COUNT(*)
                            FROM public.polls_pollsubmission ps
                            WHERE ps.poll_id = {self.obj.pk}
                        ) AS main_poll_count,
                    COALESCE
                    (
                        (
                            SELECT AVG(c) FROM (
                            SELECT COUNT(*) AS c
                            FROM public.polls_pollsubmission ps
                            JOIN public.polls_poll p
                                ON p.id = ps.poll_id
                            WHERE p.club_id = {self.obj.club.pk}
                                AND p.id <> {self.obj.pk}
                            GROUP BY ps.poll_id
                            ) _
                        ),
                        0
                    ) AS poll_average_count
                )
                SELECT
                    CASE
                        WHEN poll_average_count = 0 THEN 0
                        ELSE (main_poll_count - poll_average_count) / poll_average_count
                    END AS total_submissions_change_from_average
                FROM values;
                """
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

            return result[0]["total_submissions_change_from_average"]

    def get_submissions_heatmap(
        self, minutes: int, hours: int
    ) -> PollAnalyticsSubmissionsHeatmapSerializer:
        bin_interval = f"'{minutes} minutes'"
        interval_limit = f"'{hours} hours'"
        query = f"""
                WITH ts AS (
                    SELECT created_at AS init, close_at AS closed
                    FROM public.polls_poll
                    WHERE id = {self.obj.pk}
                )
                SELECT json_object_agg(
                    start_interval, submission_count
                ) AS submissions_heatmap
                FROM (
                    SELECT gs.interval_start AS start_interval, COUNT(ps.created_at) AS submission_count
                    FROM ts, generate_series(
                        ts.init,
                        COALESCE(ts.closed, ts.init + INTERVAL {interval_limit}),
                        INTERVAL {bin_interval}
                    ) as gs(interval_start)
                    LEFT JOIN public.polls_pollsubmission ps
                    ON ps.updated_at >= gs.interval_start
                        AND ps.updated_at < gs.interval_start + INTERVAL {bin_interval}
                        AND ps.poll_id = {self.obj.pk}
                    GROUP BY gs.interval_start
                    ORDER BY gs.interval_start
                ) AS heatmap;
                """
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = {
                "interval_minutes": minutes,
                "intervals": dictfetchall(cursor)[0]["submissions_heatmap"],
            }

            return result

    def get_questions(self):
        query = rf"""
                WITH questions AS (
                    SELECT
                        pq.id AS q_id,
                        pq.created_at,
                        pq.updated_at,
                        pq.label,
                        pq.description,
                        pq.image,
                        pq.is_required,
                        pq.input_type,
                        pq.field_id,
                        pq.is_user_lookup,
                        pq.link_user_field
                    FROM public.polls_pollfield pf
                    INNER JOIN public.polls_pollquestion pq
                    ON pf.id = pq.field_id
                    WHERE pf.poll_id = {self.obj.pk}
                ),
                answers AS (
                    SELECT *
                    FROM questions qs
                    INNER JOIN public.polls_pollquestionanswer pqa
                    ON qs.q_id = pqa.question_id
                )
                SELECT
                    q_id AS id,
                    input_type,
                    (
                        SELECT COUNT(*)
                        FROM answers
                        WHERE answers.q_id = questions.q_id
                    ) AS total_submissions,
                    (
                        SELECT json_agg(
                            json_build_object(
                                'user', ps.user_id,
                                'text_value', ans.text_value,
                                'options_value', (
                                    ARRAY(
                                        SELECT cio.label
                                        FROM questions
                                        JOIN public.polls_choiceinput ci
                                        ON ans.question_id = ci.question_id
                                        JOIN public.polls_choiceinputoption cio
                                        ON ci.id = cio.input_id
                                        WHERE ans.q_id = questions.q_id
                                        AND questions.input_type = 'choice'
                                    )
                                ),
                                'number_value', ans.number_value,
                                'boolean_value', ans.boolean_value,
                                'other_option_value', ans.other_option_value,
                                'created_at', ps.created_at
                            )
                        )
                        FROM answers ans
                        INNER JOIN public.polls_pollsubmission ps
                        ON ans.submission_id = ps.id
                        WHERE ans.q_id = questions.q_id
                    ) AS submissions,
                    (
                        SELECT json_build_object(
                            'text_input', (
                                SELECT json_build_object(
                                    'average_words', AVG(len),
                                    'max_words', MAX(len),
                                    'min_words', MIN(len)
                                )
                                FROM (
                                    SELECT array_length(regexp_split_to_array(trim(text_value), '\s+'), 1) AS len
                                    FROM answers
                                    WHERE answers.q_id = questions.q_id
                                    AND questions.input_type = 'text'
                                ) AS word_counts
                            ),
                            'email_input', (
                                json_build_object(
                                    'email_domains', (
                                        SELECT ARRAY_AGG(DISTINCT regexp_replace(trim(text_value), '.*@', ''))
                                        FROM answers
                                        WHERE answers.q_id = questions.q_id
                                        AND questions.input_type = 'email'
                                    )
                                )
                            ),
                            'checkbox_input', (
                                json_build_object(
                                    'total_true', (
                                        SELECT COUNT(*)
                                        FROM answers
                                        WHERE answers.q_id = questions.q_id
                                        AND questions.input_type = 'checkbox'
                                        AND boolean_value = TRUE
                                    )
                                )
                            ),
                            'scale_input', (
                                SELECT json_build_object(
                                    'min_value', MIN(num),
                                    'max_value', MAX(num),
                                    'mean', AVG(num),
                                    'median', (
                                        SELECT PERCENTILE_CONT(0.5)
                                        WITHIN GROUP (
                                            ORDER BY num
                                        )
                                    )
                                )
                                FROM (
                                    SELECT number_value AS num
                                    FROM answers
                                    WHERE answers.q_id = questions.q_id
                                    AND questions.input_type = 'scale'
                                ) AS nums
                            ),
                            'phone_input', (
                                json_build_object(
                                    'area_codes', (
                                        ARRAY(
                                            SELECT json_build_object(
                                                'area_code', area_code,
                                                'count', COUNT(area_code)
                                            )
                                            FROM (
                                                SELECT SUBSTRING(text_value FROM '[^-]*') AS area_code
                                                FROM answers
                                                WHERE answers.q_id = questions.q_id
                                                AND questions.input_type = 'phone'
                                            ) AS area_codes
                                            GROUP BY area_code
                                        )
                                    )
                                )
                            ),
                            'number_input', (
                                SELECT json_build_object(
                                    'min_value', MIN(num),
                                    'max_value', MAX(num),
                                    'mean', AVG(num),
                                    'median', (
                                        SELECT PERCENTILE_CONT(0.5)
                                        WITHIN GROUP (
                                            ORDER BY num
                                        )
                                    )
                                )
                                FROM (
                                    SELECT number_value AS num
                                    FROM answers
                                    WHERE answers.q_id = questions.q_id
                                    AND questions.input_type = 'number'
                                ) AS nums
                            ),
                            'url_input', (
                                SELECT json_build_object(
                                    'total_unique_domains', COUNT(unique_domain)
                                )
                                FROM (
                                    SELECT DISTINCT SUBSTRING(text_value FROM '^.*?//(.*?)(?:/|$)') AS unique_domain
                                    FROM answers
                                    WHERE answers.q_id = questions.q_id
                                    AND questions.input_type = 'url'
                                ) AS unique_domains
                            ),
                            'upload_input', (
                                json_build_object(
                                    'file_types', (
                                        ARRAY(
                                            SELECT json_build_object(
                                                'file_type', file_type,
                                                'count', COUNT(file_type)
                                            )
                                            FROM (
                                                SELECT SUBSTRING(cf.file FROM '\.(.*)') AS file_type
                                                FROM answers
                                                JOIN public.clubs_clubfile cf
                                                ON answers.file_value_id = cf.id
                                                WHERE answers.q_id = questions.q_id
                                                AND questions.input_type = 'upload'
                                            ) AS file_types
                                            GROUP BY file_type
                                        )
                                    )
                                )
                            ),
                            'date_input', (
                                json_build_object(
                                    'dates', (
                                        ARRAY(
                                            SELECT json_build_object(
                                                'date', dte,
                                                'count', COUNT(dte)
                                            )
                                            FROM (
                                                SELECT text_value AS dte
                                                FROM answers
                                                WHERE answers.q_id = questions.q_id
                                                AND questions.input_type = 'date'
                                            ) AS dtes
                                            GROUP BY dte
                                        )
                                    )
                                )
                            ),
                            'time_input', (
                                json_build_object(
                                    'times', (
                                        ARRAY(
                                            SELECT json_build_object(
                                                'time', tme,
                                                'count', COUNT(tme)
                                            )
                                            FROM (
                                                SELECT text_value AS tme
                                                FROM answers
                                                WHERE answers.q_id = questions.q_id
                                                AND questions.input_type = 'time'
                                            ) AS tmes
                                            GROUP BY tme
                                        )
                                    )
                                )
                            ),
                            'option_input', (
                                json_build_object(
                                    'options_submissions_count', (
                                        ARRAY(
                                            SELECT json_build_object(
                                                'id', option_id,
                                                'label', option_label,
                                                'total_submissions', option_count
                                            )
                                            FROM (
                                                SELECT cio.label AS option_label,
                                                    cio.id AS option_id,
                                                    COUNT(cio.id) as option_count
                                                FROM (
                                                    SELECT id AS ci_id, ci.question_id AS ci_qid
                                                    FROM public.polls_choiceinput ci
                                                    JOIN questions
                                                    ON ci.question_id = questions.q_id
                                                ) AS ci_id
                                                JOIN public.polls_choiceinputoption cio
                                                ON cio.input_id = ci_id
                                                JOIN public.polls_pollquestionanswer_options_value pqa_o_v
                                                ON cio.id = pqa_o_v.choiceinputoption_id
                                                WHERE ci_qid = questions.q_id
                                                    AND questions.input_type = 'choice'
                                                GROUP BY cio.id
                                            ) AS cios
                                        )
                                    )
                                )
                            )
                        )
                    ) AS analytics
                FROM questions;
                """
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = dictfetchall(cursor)

            return result
