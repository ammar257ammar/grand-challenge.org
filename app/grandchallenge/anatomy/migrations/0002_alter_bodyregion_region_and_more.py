# Generated by Django 4.2.7 on 2023-11-30 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("anatomy", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bodyregion",
            name="region",
            field=models.CharField(max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name="bodystructure",
            name="structure",
            field=models.CharField(max_length=16, unique=True),
        ),
    ]
