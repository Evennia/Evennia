# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-04 17:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comms', '0015_auto_20170706_2041'),
    ]

    operations = [
        migrations.AddField(
            model_name='channeldb',
            name='is_hidden',
            field=models.BooleanField(default=False),
        ),
    ]
