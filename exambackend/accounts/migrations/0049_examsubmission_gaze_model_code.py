from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0048_gazemodelselection')]

    operations = [
        migrations.AddField(
            model_name='examsubmission',
            name='gaze_model_code',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
