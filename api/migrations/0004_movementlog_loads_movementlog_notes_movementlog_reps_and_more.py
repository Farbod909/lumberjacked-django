# Generated by Django 5.1.4 on 2025-01-17 03:13

import django.contrib.postgres.fields
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_alter_workout_user_movementlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='movementlog',
            name='loads',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), default=list, size=None),
        ),
        migrations.AddField(
            model_name='movementlog',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='movementlog',
            name='reps',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.PositiveSmallIntegerField(), default=list, size=None),
        ),
        migrations.AddField(
            model_name='movementlog',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
