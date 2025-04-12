# Sending and Testing Emails

**Table of Contents**

- [Sending Emails in Django](#sending-emails-in-django)
  - [Sending "Together" vs "Separately"](#sending-together-vs-separately)
- [Examples](#examples)
  - [Simple Plain Text Emails](#simple-plain-text-emails)
  - [HTML Emails](#html-emails)
- [Testing Emails](#testing-emails)
  - [Sending with MailHog](#sending-with-mailhog)
  - [Sending with SendGrid](#sending-with-sendgrid)

## Sending Emails in Django

> Docs: <https://docs.djangoproject.com/en/5.1/topics/email/>

### Sending "Together" vs "Separately"

- **Emails Sent Together**: each person that receives the email will see each other person in the "to" field.
- **Emails Sent Separately**: each person receives the email independently

By default, email addresses in the "to" field will be sent to those emails together.

## Examples

### Simple Plain Text Emails

To send an email to _<john@example.com>_ and _<jane@example.com>_ together:

```py
from django.core.mail import send_mail

send_mail(
  subject="Example Subject",
  message="Lorem ipsum dolor sit.",
  from_email="from@example.com",
  to=["john@example.com", "jane@example.com"],
)
```

Send to _<john@example.com>_ and _<jane@example.com>_ separately:

```py
from django.core.mail import send_mail

to_emails = ["john@example.com", "jane@example.com"]

for to in to_emails:
  send_mail(
    subject="Example Subject",
    message="Lorem ipsum dolor sit.",
    from_email="from@example.com",
    to=[to],
  )
```

### HTML Emails

If an html template were created at `app/clubs/templates/clubs/sample_email.html`:

```html
<p>This is an example email.</p>
<p>Click here to learn more: <a href="{{ url }}">Link</a></p>
```

An email could be sent to _<john@example.com>_ and _<jane@example.com>_ together like this:

```py
from lib.emails import send_html_mail

send_html_mail(
    subject="Example Subject",
    to=["john@example.com", "jane@example.com"],
    html_template="clubs/sample_email.html",
    html_context={"url": "https://example.com"},
)
```

This would use the default email address when sending the email, override this by setting the `from_email` kwarg.

To send an html email to _<john@example.com>_ and _<jane@example.com>_ separately:

```py
from lib.emails import send_html_mail

send_html_mail(
    subject="Example Subject",
    to=["john@example.com", "jane@example.com"],
    html_template="clubs/sample_email.html",
    html_context={"url": "https://example.com"},
    send_separately=True
)
```

_Note: the template path starts after the `app/clubs/templates` dir._

## Testing Emails

SendGrid is used in production, but MailHog is a great utility for testing emails in development. If you want to test sending emails using a fake inbox, use MailHog, but if you want to test sending emails to actual inboxes you should test with SendGrid.

Django abstracts away the actual email service that is used, so the API/interfaces remain the same no matter which is used (so the functions mentioned in [Examples](#examples) remain the same). SendGrid vs MailHog just determines how the email is sent.

### Sending with MailHog

Make sure your `.env` file has the following variables set:

```properties
DJANGO_DEFAULT_FROM_EMAIL="admin@example.com"
DJANGO_EMAIL_HOST="mailhog"
DJANGO_EMAIL_HOST_USER=""
DJANGO_EMAIL_HOST_PASSWORD=""
DJANGO_EMAIL_PORT="1025"
DJANGO_EMAIL_USE_TLS=0
```

_Note: You can leave user and password blank, MailHog doesn't need them_

When running the normal dev command to start the server (`task dev`), a MailHog web app is automatically started up. You can access this web app at <http://localhost:8025> to see all outbound emails sent from Django. The emails aren't actually sent to their recipients, so this is a great way to test emails without accidentally spamming people's inboxes.

### Sending with SendGrid

Before you can send emails via SendGrid, you must first create an account: <https://signup.sendgrid.com>. At the time of writing, SendGrid is free if sending less than 100 email/day (pricing: <https://sendgrid.com/en-us/pricing>).

Refer to SendGrid's QuickStart documentation for creating an account and getting an API Key: <https://www.twilio.com/docs/sendgrid/for-developers/sending-email/quickstart-python>

Once you have the API Key (for example: "example-apikey"), set the email environment variables:

```properties
SENDGRID_API_KEY="example-apikey"

DJANGO_DEFAULT_FROM_EMAIL="admin@example.com"
DJANGO_EMAIL_HOST="smtp.sendgrid.net"
DJANGO_EMAIL_HOST_USER="apikey"
DJANGO_EMAIL_HOST_PASSWORD="example-apikey"
DJANGO_EMAIL_PORT="857"
DJANGO_EMAIL_USE_TLS=1
```

If you have a domain connected to SendGrid, you can replace `DJANGO_DEFAULT_FROM_EMAIL` with any email using your domain.

You can learn more about SendGrid's integration with Django here: <https://www.twilio.com/docs/sendgrid/for-developers/sending-email/django>
