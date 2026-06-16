import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0019_workouttemplate_workouttemplatemovement'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workout',
            name='start_timestamp',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
