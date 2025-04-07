from typing import Optional

from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from app.settings import DEFAULT_FROM_EMAIL


def send_html_mail(
    subject: str,
    to: list[str],
    html_template: str,
    html_context: Optional[dict] = None,
    from_email: Optional[str] = None,
    text_body=None,
    send_separately=False,
):
    """
    Send HTML email using mail.EmailMultiAlternatives class.

    Sends email to "to" recipients separately (ie they will not see eachother
    in the email app's "to" field).
    """

    html_body = render_to_string(html_template, context=html_context)

    text_body = text_body or strip_tags(html_body)
    from_email = from_email or DEFAULT_FROM_EMAIL

    if send_separately:
        for email in to:
            message = mail.EmailMultiAlternatives(
                from_email=from_email,
                subject=subject,
                body=text_body,
                to=[email],
            )
            message.attach_alternative(html_body, "text/html")
            message.send()
    else:
        message = mail.EmailMultiAlternatives(
            from_email=from_email,
            subject=subject,
            body=text_body,
            to=to,
        )
        message.attach_alternative(html_body, "text/html")
        message.send()
