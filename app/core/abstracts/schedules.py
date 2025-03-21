import json

from celery import shared_task
from django.apps import apps
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from core.abstracts.models import ModelBase
from utils.helpers import get_import_path, import_from_path


@shared_task
def run_task(model_path: str, id: int, callback_path, *args, **kwargs):
    """Central task runner for all models that inherit schedule base."""
    model = apps.get_model(model_path)
    instance: "ScheduleBase" = model.objects.get(id=id)

    callback = import_from_path(callback_path)
    callback(instance=instance, *args, **kwargs)


class ScheduleBase(ModelBase):
    """
    Base fields for models that control scheduled tasks.

    Usage
    -----
        1. Create model using interval/cron extension of this class
        2. Create signal that executes the models `schedule_task()` method
    """

    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name=_("Name"),
        help_text=_("Short Description For This Task"),
    )

    one_off = models.BooleanField(
        default=False,
        verbose_name=_("One-off Task"),
        help_text=_("If True, the schedule will only run the task a single time"),
    )

    periodic_task = models.ForeignKey(
        PeriodicTask, on_delete=models.SET_NULL, null=True, blank=True
    )

    active = models.BooleanField(default=True)

    schedule = None
    crontab = None

    class Meta:
        abstract = True

    def schedule_task(self, callback: callable, *args, **kwargs):
        """
        Creates new task with the saved schedule.
        If task already exists, delete and recreate it.

        Parameters
        ----------
            - callback (callable(instance, *args, **kwargs)): Function that calls
                when task is triggered.

        """
        if self.periodic_task:
            self.periodic_task.delete()

        params = {
            "interval": self.schedule,
            "crontab": self.crontab,
            "name": self.name,
            "task": get_import_path(run_task),
            "one_off": self.one_off,
            "args": json.dumps(
                [self.get_path(), self.pk, get_import_path(callback), *args]
            ),
            "kwargs": kwargs,
            **kwargs,
        }
        periodic_task = PeriodicTask.objects.create(**params)
        self.periodic_task = periodic_task

        self.save()

        return periodic_task

    def unschedule_task(self):
        """Remove task from schedule."""

        PeriodicTask.objects.filter(id=self.periodic_task.pk).delete()
        self.refresh_from_db()
        assert self.periodic_task is None


class IntervalScheduleBase(ScheduleBase):
    """Store info on tasks that run on a set interval."""

    schedule = models.ForeignKey(
        IntervalSchedule, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        abstract = True


class CronScheduleBase(ScheduleBase):
    """Store info for tasks that run on a cron schedule."""

    crontab = models.ForeignKey(
        CrontabSchedule, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        abstract = True
