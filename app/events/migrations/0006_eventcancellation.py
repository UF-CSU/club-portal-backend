# Generated by Django 4.2.20 on 2025-04-02 14:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('events', '0005_alter_eventtag_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventCancellation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reason', models.TextField(blank=True)),
                ('cancelled_at', models.DateTimeField(auto_now_add=True)),
                ('cancelled_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('event', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cancellation', to='events.event')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
