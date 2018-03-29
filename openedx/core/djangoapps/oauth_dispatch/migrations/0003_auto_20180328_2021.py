# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oauth_dispatch', '0002_auto_20180327_2207'),
    ]

    operations = [
        migrations.AlterField(
            model_name='restrictedapplication',
            name='_allowed_scopes',
            field=models.TextField(default=b'write profile enrollments:read grades:read grades:statistics read email certificates:read', null=True),
        ),
    ]
