# Generated by Django 3.1.1 on 2020-12-17 06:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
        ("algorithms", "0002_auto_20201214_0939"),
    ]

    operations = [
        migrations.AddField(
            model_name="algorithm",
            name="organizations",
            field=models.ManyToManyField(
                blank=True,
                help_text="The organizations associated with this algorithm",
                related_name="algorithms",
                to="organizations.Organization",
            ),
        )
    ]
