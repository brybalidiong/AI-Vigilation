from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0046_examsubmission_iris_verified_at')]

    operations = [
        migrations.AddField(
            model_name='examsubmission',
            name='gaze_glance_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='examsubmission',
            name='gaze_glance_last_frame_hash',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
