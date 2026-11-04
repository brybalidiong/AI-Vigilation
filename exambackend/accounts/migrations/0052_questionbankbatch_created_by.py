from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_batches(apps, schema_editor):
    Batch = apps.get_model('accounts', 'QuestionBankBatch')
    for batch in Batch.objects.filter(created_by__isnull=True).select_related('subject').iterator():
        batch.created_by_id = batch.subject.instructor_id
        batch.save(update_fields=['created_by'])


class Migration(migrations.Migration):
    dependencies = [('accounts', '0051_examset_created_by')]
    operations = [
        migrations.AddField(
            model_name='questionbankbatch', name='created_by',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL,
                related_name='question_bank_batches', null=True, blank=True,
            ),
        ),
        migrations.RunPython(assign_legacy_batches, migrations.RunPython.noop),
    ]
