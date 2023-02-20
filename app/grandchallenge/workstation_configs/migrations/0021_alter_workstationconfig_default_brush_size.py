# Generated by Django 3.2.18 on 2023-02-20 13:14

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workstation_configs", "0020_auto_20230116_1358"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workstationconfig",
            name="default_brush_size",
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                help_text="Default brush diameter in millimeters for creating annotations",
                max_digits=16,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(limit_value=1e-06)
                ],
            ),
        ),
    ]
