# Generated by Django 3.1.1 on 2020-12-02 13:08

import uuid

import django.db.models.deletion
from django.db import migrations, models

import grandchallenge.core.storage
import grandchallenge.uploads.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("challenges", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="SummernoteAttachment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True,
                        help_text="Defaults to filename, if left blank",
                        max_length=255,
                        null=True,
                    ),
                ),
                ("uploaded", models.DateTimeField(auto_now_add=True)),
                (
                    "file",
                    models.FileField(
                        storage=grandchallenge.core.storage.PublicS3Storage(),
                        upload_to=grandchallenge.uploads.models.summernote_upload_filepath,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="PublicMedia",
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
                (
                    "file",
                    models.FileField(
                        storage=grandchallenge.core.storage.PublicS3Storage(),
                        upload_to=grandchallenge.uploads.models.public_media_filepath,
                    ),
                ),
                (
                    "challenge",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="challenges.challenge",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
