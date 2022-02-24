# Generated by Django 3.1.11 on 2021-07-21 14:27

from django.db import migrations, models

import grandchallenge.core.validators


class Migration(migrations.Migration):
    dependencies = [("components", "0004_auto_20210601_0802")]

    operations = [
        migrations.AddField(
            model_name="componentinterface",
            name="schema",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Additional JSON schema that the values for this interface must satisfy. See https://json-schema.org/. Only Draft 7, 6, 4 or 3 are supported.",
                validators=[
                    grandchallenge.core.validators.JSONSchemaValidator()
                ],
            ),
        )
    ]
