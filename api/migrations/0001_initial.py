# Generated by Django 5.1.4 on 2025-01-15 06:59

import django.db.models.deletion
import lumberjacked.utils
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Movement',
            fields=[
                ('id', models.BigIntegerField(default=lumberjacked.utils.generate_id, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('category', models.CharField(blank=True, max_length=100)),
                ('notes', models.TextField(blank=True)),
                ('created_timestamp', models.DateTimeField(auto_now_add=True)),
                ('updated_timestamp', models.DateTimeField(auto_now=True)),
                ('recommended_warmup_sets', models.CharField(blank=True, max_length=7)),
                ('recommended_working_sets', models.CharField(blank=True, max_length=7)),
                ('recommended_rep_range', models.CharField(blank=True, max_length=7)),
                ('recommended_rpe', models.CharField(blank=True, max_length=7)),
                ('recommended_rest_time', models.PositiveSmallIntegerField(null=True)),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
