# Generated by Django 3.2.13 on 2022-07-07 09:33

import django.db.models.deletion
from django.db import migrations, models

import grandchallenge.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("workstations", "0010_workstationimage_latest_shimmed_version"),
        ("hanging_protocols", "0004_alter_hangingprotocol_json"),
        ("workstation_configs", "0015_auto_20220607_0841"),
        ("evaluation", "0026_evaluation_attempt"),
    ]

    operations = [
        migrations.AddField(
            model_name="phase",
            name="hanging_protocol",
            field=models.ForeignKey(
                blank=True,
                help_text='Indicate which Component Interfaces need to be displayed in which image port. E.g. {"main": ["interface1"]}. The first item in the list of interfaces will be the main image in the image port. The first overlay type interface thereafter will be rendered as an overlay. For now, any other items will be ignored by the viewer.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="hanging_protocols.hangingprotocol",
            ),
        ),
        migrations.AddField(
            model_name="phase",
            name="view_content",
            field=models.JSONField(
                blank=True,
                default=dict,
                validators=[
                    grandchallenge.core.validators.JSONValidator(
                        schema={
                            "$schema": "http://json-schema.org/draft-06/schema#",
                            "additionalProperties": False,
                            "definitions": {},
                            "properties": {
                                "denary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "duodenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "main": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "nonary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "novemdenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "octodenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "octonary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "quaternary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "quattuordenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "quinary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "quindenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "secondary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "senary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "septenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "septendenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "sexdenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "tertiary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "tredenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "undenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                                "vigintenary": {
                                    "contains": {"type": "string"},
                                    "minItems": 1,
                                    "type": "array",
                                    "uniqueItems": True,
                                },
                            },
                            "title": "The Display Port Mapping Schema",
                            "type": "object",
                        }
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="phase",
            name="workstation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="workstations.workstation",
            ),
        ),
        migrations.AddField(
            model_name="phase",
            name="workstation_config",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="workstation_configs.workstationconfig",
            ),
        ),
    ]
