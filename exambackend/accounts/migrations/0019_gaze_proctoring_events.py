from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_proctoring_reports'),
    ]

    operations = [
        migrations.AlterField(
            model_name='examproctoringevent',
            name='event_type',
            field=models.CharField(
                max_length=40,
                choices=[
                    ('tab_switch', 'Tab switch'),
                    ('window_blur', 'Window blur'),
                    ('window_focus', 'Window focus'),
                    ('visibility_hidden', 'Tab hidden'),
                    ('visibility_visible', 'Tab visible'),
                    ('split_screen', 'Split screen'),
                    ('copy_attempt', 'Copy attempt'),
                    ('cut_attempt', 'Cut attempt'),
                    ('screenshot_attempt', 'Screenshot attempt'),
                    ('right_click', 'Right click'),
                    ('exam_started', 'Exam started'),
                    ('exam_submitted', 'Exam submitted'),
                    ('exam_terminated', 'Exam terminated'),
                    ('time_up', 'Time up'),
                    ('periodic_capture', 'Periodic capture'),
                    ('gaze_violation', 'Gaze away from screen'),
                    ('gaze_no_face', 'Face not visible'),
                ],
            ),
        ),
    ]
