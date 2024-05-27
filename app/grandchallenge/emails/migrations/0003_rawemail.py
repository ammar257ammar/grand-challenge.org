# Generated by Django 4.2.11 on 2024-04-12 10:34

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0002_alter_email_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="RawEmail",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("message", models.TextField(editable=False)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ("-created",),
            },
        ),
    ]