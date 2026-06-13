from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_movementlogtemplate'),
    ]

    operations = [
        migrations.RemoveField(model_name='movement', name='recommended_warmup_sets'),
        migrations.RemoveField(model_name='movement', name='recommended_working_sets'),
        migrations.RemoveField(model_name='movement', name='recommended_rep_range'),
        migrations.RemoveField(model_name='movement', name='recommended_rpe'),
        migrations.RemoveField(model_name='movement', name='recommended_rest_time'),
    ]
