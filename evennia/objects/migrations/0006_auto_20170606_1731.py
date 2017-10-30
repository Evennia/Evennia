# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-06 17:31


import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0005_auto_20150403_2339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='objectdb',
            name='db_attributes',
            field=models.ManyToManyField(help_text=b'attributes on this object. An attribute can hold any pickle-able python object (see docs for special cases).', to='typeclasses.Attribute'),
        ),
        migrations.AlterField(
            model_name='objectdb',
            name='db_sessid',
            field=models.CharField(help_text=b'csv list of session ids of connected Account, if any.', max_length=32, null=True, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:\\,\\d+)*\\Z'), code='invalid', message='Enter only digits separated by commas.')], verbose_name=b'session id'),
        ),
        migrations.AlterField(
            model_name='objectdb',
            name='db_tags',
            field=models.ManyToManyField(help_text=b'tags on this object. Tags are simple string markers to identify, group and alias objects.', to='typeclasses.Tag'),
        ),
    ]
