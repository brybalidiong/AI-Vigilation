from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0041_subject_archived_by')]

    operations = [
        migrations.AddField(
            model_name='examset',
            name='allow_backtracking',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='examsubmission',
            name='question_index',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='examsubmission',
            name='locked_answers',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
