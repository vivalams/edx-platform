# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0006_auto_20171207_0259'),
        ('oauth_dispatch', '0002_auto_20161016_0926'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='restrictedapplication',
            name='_org_associations',
        ),
        migrations.AddField(
            model_name='restrictedapplication',
            name='_org_associations',
            field=models.ManyToManyField(to='organizations.Organization'),
        ),
    ]
