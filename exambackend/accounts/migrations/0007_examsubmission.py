from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_examset_due_at_exam_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_email', models.EmailField(max_length=254)),
                ('is_done', models.BooleanField(default=False)),
                ('score', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('integrity_score', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('exam_set', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='submissions', to='accounts.examset')),
            ],
            options={
                'ordering': ['student_email'],
                'constraints': [
                    models.UniqueConstraint(fields=('exam_set', 'student_email'), name='unique_submission_per_exam_student'),
                ],
            },
        ),
    ]
