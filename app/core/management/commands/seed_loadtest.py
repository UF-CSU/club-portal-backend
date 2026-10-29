"""
Seed a database with synthetic data for load testing.

Only run this against a throwaway database: it adds thousands of fake users, clubs,
events, polls and submissions. All emails use the reserved example.edu domain.

Usage:
    python manage.py seed_loadtest --confirm <db name> --tokens-out /tmp/tokens.json
"""

import json
import random
from datetime import timedelta

from clubs.models import Club
from clubs.services import ClubService
from core.abstracts.models import RoleType
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import override_settings
from django.utils import timezone
from events.models import Event, EventAttendance, EventStatus
from lib.faker import fake
from polls.models import (
    ChoiceInputOption,
    Poll,
    PollInputType,
    PollQuestionAnswer,
    PollStatusType,
    PollSubmission,
    PollUserFieldType,
)
from polls.services import PollService
from rest_framework.authtoken.models import Token
from users.models import User

PASSWORD = "loadtest-password"
YEARS = ["Freshman", "Sophomore", "Junior", "Senior", "Graduate"]
SOURCES = ["Instagram", "Friend", "Club fair", "Email", "Word of mouth"]
MAJORS = ["Computer Science", "Biology", "Finance", "Psychology", "Engineering"]


class Command(BaseCommand):
    help = "Seed synthetic load test data (users, clubs, events, polls, submissions)."

    def add_arguments(self, parser):
        parser.add_argument("--confirm", required=True, help="Name of the target database")
        parser.add_argument("--scale", type=float, default=1.0)
        parser.add_argument("--tokens-out", default="/tmp/loadtest-tokens.json")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        db_name = connection.settings_dict["NAME"]
        if options["confirm"] != db_name:
            raise CommandError(f"--confirm must match the target database name ({db_name}).")

        random.seed(options["seed"])
        fake.seed_instance(options["seed"])
        s = options["scale"]
        now = timezone.now()

        users = self.create_users(int(10_000 * s))
        clubs = self.create_clubs(int(1_200 * s))
        active = random.sample(clubs, int(len(clubs) * 0.25))
        self.create_memberships(active, users)
        events = self.create_events(active, int(3_000 * s), now)
        self.create_polls(events, users, now)
        live = self.create_live_event(active[0], now)
        self.write_tokens(users, options["tokens_out"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(users)} users, {len(clubs)} clubs, {len(events)} events. "
                f"Live poll id: {live.id}. Tokens: {options['tokens_out']}"
            )
        )

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
    def create_users(self, count: int) -> list[User]:
        self.stdout.write(f"Creating {count} users...")
        users = []
        for i in range(count):
            users.append(
                User.objects.create_user(
                    email=f"student{i:06d}@example.edu", password=PASSWORD, name=fake.name()
                )
            )
        return users

    def create_clubs(self, count: int) -> list[Club]:
        self.stdout.write(f"Creating {count} clubs...")
        return [
            Club.objects.create(
                name=f"{fake.title(2)} Club {i}",
                alias=f"LT{i:05d}",
                is_csu_partner=random.random() < 0.3,
            )
            for i in range(count)
        ]

    def create_memberships(self, clubs: list[Club], users: list[User]):
        self.stdout.write(f"Creating memberships for {len(clubs)} active clubs...")
        for club in clubs:
            svc = ClubService(club)
            admin_role = club.roles.filter(role_type=RoleType.ADMIN).first()
            members = random.sample(users, random.randint(20, 150))

            for user in members[:2]:
                svc.add_member(user, roles=[admin_role])
            for user in members[2:]:
                svc.add_member(user)

    def create_events(self, clubs: list[Club], count: int, now) -> list[Event]:
        self.stdout.write(f"Creating {count} events...")
        events = []
        for _ in range(count):
            start = now + timedelta(days=random.uniform(-730, 30), hours=random.randint(-6, 6))
            events.append(
                Event.objects.create(
                    name=fake.title(),
                    location=fake.address(),
                    description=fake.paragraph(),
                    start_at=start,
                    end_at=start + timedelta(hours=random.choice([1, 2, 3])),
                    host=random.choice(clubs),
                    status=EventStatus.PUBLISHED,
                    is_public=random.random() < 0.85,
                )
            )
        return events

    def create_form(self, club: Club, event: Event | None, name: str) -> Poll:
        """Create a poll shaped like a real event sign-in form."""

        poll = Poll.objects.create(name=name, club=club, event=event)
        svc = PollService(poll)

        svc.create_question(
            "Name", is_required=True, link_user_field=PollUserFieldType.NAME
        )
        for label, values in [
            ("Year", YEARS),
            ("Major", MAJORS),
            ("How did you hear about us?", SOURCES),
        ]:
            question = svc.create_question(label, input_type=PollInputType.CHOICE)
            for order, value in enumerate(values):
                ChoiceInputOption.objects.create(
                    input=question.choice_input, order=order, label=value, value=value
                )
        svc.create_question("Anything else?")

        return poll

    def create_polls(self, events: list[Event], users: list[User], now):
        with_forms = [e for e in events if random.random() < 0.4]
        self.stdout.write(f"Creating {len(with_forms)} polls with submissions...")

        for event in with_forms:
            poll = self.create_form(event.primary_club, event, f"{event.name} sign in")
            is_past = event.end_at < now
            status = PollStatusType.CLOSED if is_past else PollStatusType.SCHEDULED
            Poll.objects.filter(id=poll.id).update(status=status)

            if is_past:
                self.bulk_submissions(poll, random.sample(users, random.randint(10, 150)))

    @transaction.atomic
    def bulk_submissions(self, poll: Poll, users: list[User]):
        """Insert historical submissions directly, skipping per-row signals."""

        questions = list(poll.questions.select_related("field"))
        options = {
            q.id: list(q.choice_input.options.all())
            for q in questions
            if q.input_type == PollInputType.CHOICE
        }

        submissions = PollSubmission.objects.bulk_create(
            [PollSubmission(poll=poll, user=u) for u in users]
        )

        answers, choices = [], []
        for sub, user in zip(submissions, users):
            for q in questions:
                answer = PollQuestionAnswer(question=q, submission=sub)
                if q.is_user_lookup:
                    answer.text_value = user.email
                elif q.link_user_field == PollUserFieldType.NAME:
                    answer.text_value = user.profile.name or "Student"
                elif q.id in options:
                    choices.append((answer, random.choice(options[q.id])))
                else:
                    answer.text_value = fake.sentence() if random.random() < 0.3 else None
                answers.append(answer)

        PollQuestionAnswer.objects.bulk_create(answers)
        Through = PollQuestionAnswer.options_value.through
        Through.objects.bulk_create(
            [
                Through(pollquestionanswer_id=a.id, choiceinputoption_id=o.id)
                for a, o in choices
            ]
        )
        EventAttendance.objects.bulk_create(
            [EventAttendance(event=poll.event, user=u) for u in users],
            ignore_conflicts=True,
        )

    def create_live_event(self, club: Club, now) -> Poll:
        """An event happening now with an open, empty form: the submit burst target."""

        event = Event.objects.create(
            name="Live General Body Meeting",
            location="Reitz Union",
            start_at=now - timedelta(minutes=30),
            end_at=now + timedelta(hours=2),
            host=club,
            status=EventStatus.PUBLISHED,
        )
        poll = self.create_form(club, event, "Live GBM sign in")
        Poll.objects.filter(id=poll.id).update(status=PollStatusType.OPEN)
        return poll

    def write_tokens(self, users: list[User], path: str):
        tokens = [Token(user=u) for u in users]
        Token.objects.filter(user__in=users).delete()
        for t in tokens:
            t.key = t.generate_key()
        Token.objects.bulk_create(tokens)

        with open(path, "w") as f:
            json.dump(
                [{"user_id": t.user_id, "email": t.user.email, "token": t.key} for t in tokens],
                f,
            )
