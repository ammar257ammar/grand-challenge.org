# Generated by Django 3.1.6 on 2021-02-28 18:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("knox", "0007_auto_20190111_0542"),
        ("workstations", "0001_squashed_0011_auto_20201001_0758"),
    ]

    operations = [
        migrations.AddField(
            model_name="session",
            name="auth_token",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="knox.authtoken",
            ),
        )
    ]
