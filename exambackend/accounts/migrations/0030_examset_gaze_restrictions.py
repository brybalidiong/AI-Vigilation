from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0029_studentanswer_awarded_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='examset',
            name='detect_gaze_above',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='examset',
            name='detect_gaze_below',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='examset',
            name='detect_gaze_left',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='examset',
            name='detect_gaze_right',
            field=models.BooleanField(default=True),
        ),
    ]
