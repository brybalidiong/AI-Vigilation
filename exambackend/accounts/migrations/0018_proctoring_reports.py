# Generated manually for proctoring integrity reports

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_subject_display_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamProctoringEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt_number', models.PositiveIntegerField(default=1)),
                ('event_type', models.CharField(choices=[('tab_switch', 'Tab switch'), ('window_blur', 'Window blur'), ('window_focus', 'Window focus'), ('visibility_hidden', 'Tab hidden'), ('visibility_visible', 'Tab visible'), ('split_screen', 'Split screen'), ('copy_attempt', 'Copy attempt'), ('cut_attempt', 'Cut attempt'), ('screenshot_attempt', 'Screenshot attempt'), ('right_click', 'Right click'), ('exam_started', 'Exam started'), ('exam_submitted', 'Exam submitted'), ('exam_terminated', 'Exam terminated'), ('time_up', 'Time up'), ('periodic_capture', 'Periodic capture')], max_length=40)),
                ('severity', models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')], default='warning', max_length=10)),
                ('message', models.TextField(blank=True, default='')),
                ('source', models.CharField(blank=True, default='', max_length=80)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proctoring_events', to='accounts.examsubmission')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='ExamProctoringEvidence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt_number', models.PositiveIntegerField(default=1)),
                ('evidence_type', models.CharField(choices=[('webcam', 'Webcam'), ('screen', 'Screen')], default='webcam', max_length=20)),
                ('image', models.ImageField(upload_to='proctoring_evidence/%Y/%m/')),
                ('caption', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='evidence', to='accounts.examproctoringevent')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proctoring_evidence', to='accounts.examsubmission')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='ExamIntegrityReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt_number', models.PositiveIntegerField(default=1)),
                ('integrity_score', models.DecimalField(decimal_places=2, max_digits=6)),
                ('event_count', models.PositiveIntegerField(default=0)),
                ('warning_count', models.PositiveIntegerField(default=0)),
                ('critical_count', models.PositiveIntegerField(default=0)),
                ('evidence_count', models.PositiveIntegerField(default=0)),
                ('tab_switch_count', models.PositiveIntegerField(default=0)),
                ('summary', models.JSONField(blank=True, default=dict)),
                ('narrative', models.TextField(blank=True, default='')),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='integrity_reports', to='accounts.examsubmission')),
            ],
            options={
                'ordering': ['-generated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='examproctoringevent',
            index=models.Index(fields=['submission', 'attempt_number'], name='accounts_ex_submiss_6a8f2d_idx'),
        ),
        migrations.AddIndex(
            model_name='examproctoringevent',
            index=models.Index(fields=['event_type'], name='accounts_ex_event_t_0e4b1a_idx'),
        ),
        migrations.AddIndex(
            model_name='examproctoringevidence',
            index=models.Index(fields=['submission', 'attempt_number'], name='accounts_ex_submiss_9c3d4e_idx'),
        ),
        migrations.AddConstraint(
            model_name='examintegrityreport',
            constraint=models.UniqueConstraint(fields=('submission', 'attempt_number'), name='unique_integrity_report_per_attempt'),
        ),
    ]
