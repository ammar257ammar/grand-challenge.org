# Generated by Django 3.1.13 on 2021-11-01 20:17

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("cases", "0007_remove_image_study")]

    operations = [migrations.DeleteModel(name="RawImageFile")]
