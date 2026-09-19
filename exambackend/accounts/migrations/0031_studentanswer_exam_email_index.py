from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0030_examset_gaze_restrictions'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='studentanswer',
            index=models.Index(
                fields=['exam_set', 'student_email'],
                name='acct_answer_exam_email_idx',
            ),
        ),
    ]
