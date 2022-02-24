# Generated by Django 3.1.2 on 2020-12-20 22:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("forum_conversation", "0012_auto_20200423_1049")]

    operations = [
        migrations.AlterField(
            model_name="topic",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, verbose_name="Creation date"
            ),
        ),
        migrations.AlterField(
            model_name="topic",
            name="last_post_on",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="Last post added on",
            ),
        ),
        migrations.AlterField(
            model_name="topic",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, db_index=True, verbose_name="Update date"
            ),
        ),
        migrations.AddIndex(
            model_name="topic",
            index=models.Index(
                fields=["type", "last_post_on"],
                name="forum_conve_type_cc96d0_idx",
            ),
        ),
    ]
