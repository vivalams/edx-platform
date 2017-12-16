# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0010_auto_20171203_1216'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseenrollment',
            name='site',
        ),
        migrations.RemoveField(
            model_name='historicalcourseenrollment',
            name='site',
        ),
    ]
