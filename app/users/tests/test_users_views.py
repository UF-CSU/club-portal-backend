import re

from bs4 import BeautifulSoup
from core.abstracts.tests import EmailTestsBase, PublicViewTestsBase
from django.core import mail
from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status

from users.services import UserService
from users.tests.utils import create_test_user


class UserAuthViewTests(PublicViewTestsBase, EmailTestsBase):
    """Unit tests for user views, including user auth views."""

    def test_account_setup_flow(self):
        """Should allow user to setup account on client side."""

        user = create_test_user()

        # 1. Send user setup link
        UserService(user).send_account_setup_link()

        self.assertEmailsSent(1)

        # 2. User clicks link, sending them to client side which now has access to the uid & code
        email: mail.EmailMultiAlternatives = self.outbox[0]
        email_content = email.alternatives[0][0]
        soup = BeautifulSoup(email_content, "html.parser")
        el = soup.select("a#setup-link")
        self.assertEqual(len(el), 1)
        el = el[0]

        url = el.get("href")
        uid, code = re.search(r"uidb64=(.*)&code=(.*)", url).groups()

        # 3. Verify uid & code, redirect back to client with token
        verify_url = (
            reverse(
                "users:verify_setup_account",
                kwargs={"uidb64": uid, "token": code},
            )
            + "?next=http://example.com"
        )
        res: HttpResponseRedirect = self.client.get(verify_url)
        self.assertEqual(res.status_code, status.HTTP_302_FOUND)
        next_url = res.url
        next_url_token = re.search(r"token=(.*)", next_url).groups()[0]

        # 4. Client can now authenticate with token
        me_url = reverse("api-users:me")
        me_res = self.client.get(
            me_url, headers={"Authorization": f"Token {next_url_token}"}
        )
        self.assertResOk(me_res)
        user_id = me_res.json().get("id")
        self.assertEqual(user_id, user.id)
