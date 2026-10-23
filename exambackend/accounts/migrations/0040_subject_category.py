from django.db import migrations, models


def classify_existing_courses(apps, schema_editor):
    Subject = apps.get_model('accounts', 'Subject')
    UserProfile = apps.get_model('accounts', 'UserProfile')
    institute_by_instructor = dict(
        UserProfile.objects.filter(role='instructor').values_list('user_id', 'institute')
    )
    valid = {'IC', 'ITED', 'IASS', 'ILEGG'}
    for subject in Subject.objects.all().only('id', 'instructor_id').iterator():
        institute = institute_by_instructor.get(subject.instructor_id)
        if institute in valid:
            Subject.objects.filter(pk=subject.pk).update(category=institute)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0039_extended_monitor_event')]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='additional_instructors',
            field=models.ManyToManyField(blank=True, related_name='additional_subjects', to='auth.user'),
        ),
        migrations.AddField(
            model_name='subject',
            name='category',
            field=models.CharField(
                blank=True, choices=[
                    ('IC', 'Institute of Computing'),
                    ('ITED', 'Institute of Teachers Education'),
                    ('IASS', 'Institute of Acquatic and Applied Sciences'),
                    ('ILEGG', 'Institute of Leadership, Entrepreneurship and Good Governance'),
                    ('MINOR', 'Minor courses'),
                ], default='', max_length=5,
            ),
        ),
        migrations.RunPython(classify_existing_courses, migrations.RunPython.noop),
    ]
