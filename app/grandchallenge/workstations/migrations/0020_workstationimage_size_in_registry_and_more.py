# Generated by Django 4.1.10 on 2023-08-25 16:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "workstations",
            "0019_workstationimage_storage_cost_per_year_usd_millicents",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="workstationimage",
            name="size_in_registry",
            field=models.PositiveBigIntegerField(
                default=0,
                editable=False,
                help_text="The number of bytes stored in the registry",
            ),
        ),
        migrations.AddField(
            model_name="workstationimage",
            name="size_in_storage",
            field=models.PositiveBigIntegerField(
                default=0,
                editable=False,
                help_text="The number of bytes stored in the storage backend",
            ),
        ),
    ]