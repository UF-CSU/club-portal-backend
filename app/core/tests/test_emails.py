from django.core import mail

from core.abstracts.tests import TestsBase
from lib.faker import fake


class CoreEmailsTests(TestsBase):
    """Unit tests for core email functionality."""

    def test_send_email(self):
        """Should send an email via email backend."""

        subject = fake.title(4)
        message = fake.paragraph(5)
        mail.send_mail(
            subject=subject,
            message=message,
            recipient_list=["user@example.com"],
            from_email="admin@example.com",
        )

        self.assertEqual(len(mail.outbox), 1)
