# Generated by Django 5.1.4 on 2025-01-28 07:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_alter_movementlog_timestamp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movementlog',
            name='movement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movement_logs', to='api.movement'),
        ),
        migrations.AlterField(
            model_name='workout',
            name='end_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
