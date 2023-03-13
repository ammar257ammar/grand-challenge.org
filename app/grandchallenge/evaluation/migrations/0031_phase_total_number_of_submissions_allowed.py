# Generated by Django 3.2.18 on 2023-03-09 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "evaluation",
            "0030_evaluationgroupobjectpermission_evaluationuserobjectpermission_methodgroupobjectpermission_methoduse",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="phase",
            name="total_number_of_submissions_allowed",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Total number of submissions allowed for this phase for all users together.",
                null=True,
            ),
        ),
    ]