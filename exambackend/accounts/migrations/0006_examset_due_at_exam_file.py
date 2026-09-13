from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_studentset_subject'),
    ]

    operations = [
        migrations.AddField(
            model_name='examset',
            name='due_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='examset',
            name='exam_file',
            field=models.FileField(blank=True, null=True, upload_to='exam_uploads/'),
        ),
    ]
