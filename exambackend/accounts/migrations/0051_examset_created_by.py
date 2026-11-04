from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_exams(apps, schema_editor):
    ExamSet = apps.get_model('accounts', 'ExamSet')
    for exam in ExamSet.objects.filter(created_by__isnull=True).select_related('subject').iterator():
        exam.created_by_id = exam.subject.instructor_id
        exam.save(update_fields=['created_by'])


class Migration(migrations.Migration):
    dependencies = [('accounts', '0050_assign_legacy_course_sections')]
    operations = [
        migrations.AddField(
            model_name='examset', name='created_by',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_exam_sets', null=True, blank=True,
            ),
        ),
        migrations.RunPython(assign_legacy_exams, migrations.RunPython.noop),
    ]
