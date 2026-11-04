from django.db import migrations


def assign_legacy_sections(apps, schema_editor):
    StudentSet = apps.get_model('accounts', 'StudentSet')
    for roster in StudentSet.objects.filter(subject__isnull=False, created_by__isnull=True).select_related('subject').iterator():
        roster.created_by_id = roster.subject.instructor_id
        roster.save(update_fields=['created_by'])


class Migration(migrations.Migration):
    dependencies = [('accounts', '0049_examsubmission_gaze_model_code')]
    operations = [migrations.RunPython(assign_legacy_sections, migrations.RunPython.noop)]
