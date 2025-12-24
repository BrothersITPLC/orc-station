import os
import secrets
import string
import threading
from datetime import datetime
from uuid import uuid4

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from exceptions import EmailSendError


def generate_verification_token(user):
    # Generate a random verification token
    token_length = 32
    letters_and_digits = string.ascii_letters + string.digits
    verification_token = "".join(
        secrets.choice(letters_and_digits) for i in range(token_length)
    )

    return verification_token


def send_verification_email(user, request=None):
    # Generate and save verification token to user model (example)
    verification_token = generate_verification_token(user)
    user.email_verification_token = verification_token
    user.save()

    # Construct verification link

    verification_link = reverse("verify-email", kwargs={"token": verification_token})
    verification_url = f"http://0.0.0.0:8000{verification_link}"

    # Render email template
    html_message = render_to_string(
        "verification_email.html", {"user": user, "verification_link": verification_url}
    )
    plain_message = strip_tags(html_message)

    # Send email
    subject = "Verify Your Email"
    from_email = "hodadisbirhan80@gmail.com"
    to_email = user.email
    try:
        send_mail(
            subject, plain_message, from_email, [to_email], html_message=html_message
        )
    except Exception as e:
        print(e)
        raise EmailSendError("Failed to send verification email")
    return verification_token


_thread_locals = threading.local()


def get_current_user():
    return getattr(_thread_locals, "user", None)


def set_current_user(user):
    _thread_locals.user = user


def uploadTo(instance, filename):
    # Extract the file extension
    ext = filename.split(".")[-1]
    # Generate a unique filename using UUID
    unique_filename = f"{uuid4().hex}.{ext}"

    # Optional: Organize by date
    date_path = datetime.now().strftime("%Y/%m/%d")

    # Construct the final upload path
    return os.path.join(
        "posts",
        instance.__class__.__name__.lower(),
        str(instance.pk)
        or "unassigned",  # Instance ID or 'unassigned' if instance hasn't been saved yet
        date_path,
        unique_filename,
    )
