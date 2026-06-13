import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import lumberjacked.utils


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_remove_movementlog_loads_remove_movementlog_reps_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MovementLogTemplate',
            fields=[
                ('id', models.PositiveBigIntegerField(default=lumberjacked.utils.generate_id, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('sets', models.JSONField(default=list)),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('movement', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='templates', to='api.movement')),
            ],
        ),
    ]
