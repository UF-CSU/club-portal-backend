"""
Api Views for core app functionalities.
"""

from datetime import datetime, timedelta

import sentry_sdk
from celery import Celery
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import exception_handler

from app.settings import S3_STORAGE_BACKEND
from clubs.models import Club
from utils.admin import get_admin_context
from utils.logging import print_error


def index(request):
    """Base view for site."""
    server_time = timezone.now().strftime("%d/%m/%Y, %H:%M:%S")
    clubs = Club.objects.find()

    return render(request, "core/landing.html", context={"time": server_time, "clubs": clubs})


async def health_check(request):
    """API Health Check."""
    payload = {"status": 200, "message": "Systems operational."}

    await Club.objects.afirst()

    return JsonResponse(payload, status=200)


def api_exception_handler(exc, context):
    """Custom exception handler for api."""
    response = exception_handler(exc, context)

    if response is not None:
        response.data["status_code"] = response.status_code
    else:
        print_error()
        response = Response({"status_code": 400, "detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

    return response


@login_required
@staff_member_required
def sys_info(request):
    """View system info."""

    context = get_admin_context(request)
    context["services"] = {}

    # Redis
    try:
        cache.set("test", "test-value")
        value = cache.get("test")
        assert value == "test-value", f"Received invalid cache value: {value}"
        redis_status = "Online"
    except Exception as e:
        redis_status = "Offline"
        print_error()
        sentry_sdk.capture_exception(e)

    context["services"]["Redis"] = redis_status

    # Celery
    try:
        app = Celery()
        app.control.heartbeat  # noqa: B018
        celery_status = "Online"
    except Exception:
        celery_status = "Offline"
        print_error()

    context["services"]["Celery"] = celery_status

    # Celery Beat
    try:
        heartbeat_obj = PeriodicTask.objects.filter(name="heartbeat")
        if not heartbeat_obj.exists():
            cb_status = "No Heartbeat"
        else:
            heartbeat_obj = heartbeat_obj.first()
            delta = datetime.now(timezone.utc) - heartbeat_obj.last_run_at

            assert delta < timedelta(
                minutes=2
            ), f"Last heart beat was greater than 2 minutes ago: {delta}"

            cb_status = "Online"
    except Exception as e:
        cb_status = "Offline"
        print_error()
        sentry_sdk.capture_exception(e)

    context["services"]["Celery Beat"] = cb_status

    # S3 Backend
    if S3_STORAGE_BACKEND:
        try:
            default_storage.save(
                "heartbeat.txt",
                ContentFile("File was generated to test if s3 connection worked."),
            )
            assert default_storage.exists("heartbeat.txt")
            s3_status = "Online"
            default_storage.delete("heartbeat.txt")

        except Exception as e:
            s3_status = "Offline"
            print_error()
            sentry_sdk.capture_exception(e)
    else:
        s3_status = "Disabled"

    context["services"]["S3 Backend"] = s3_status

    return render(request, "core/system_info.html", context=context)
