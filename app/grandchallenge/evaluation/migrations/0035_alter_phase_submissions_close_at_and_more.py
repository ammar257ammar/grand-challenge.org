# Generated by Django 4.1.8 on 2023-05-04 10:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "evaluation",
            "0034_alter_evaluation_inputs_alter_evaluation_outputs_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="phase",
            name="submissions_close_at",
            field=models.DateTimeField(
                blank=True,
                help_text="If set, participants will not be able to make submissions to this phase after this time. Enter the date and time in your local timezone.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="phase",
            name="submissions_open_at",
            field=models.DateTimeField(
                blank=True,
                help_text="If set, participants will not be able to make submissions to this phase before this time. Enter the date and time in your local timezone.",
                null=True,
            ),
        ),
    ]
