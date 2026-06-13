from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_alter_movement_category'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='movementlog',
            name='loads',
        ),
        migrations.RemoveField(
            model_name='movementlog',
            name='reps',
        ),
        migrations.AddField(
            model_name='movementlog',
            name='sets',
            field=models.JSONField(default=list),
        ),
    ]
