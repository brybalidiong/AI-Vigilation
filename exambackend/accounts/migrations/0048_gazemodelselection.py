from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0047_examsubmission_gaze_glances')]

    operations = [
        migrations.CreateModel(
            name='GazeModelSelection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_code', models.CharField(default='efficientnet', max_length=20)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
