from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_gaze_proctoring_events'),
    ]

    operations = [
        migrations.AddField(
            model_name='examintegrityreport',
            name='gaze_violation_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='examintegrityreport',
            name='gaze_no_face_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
