from django.db import migrations, models
import django.db.models.deletion


def group_existing_questions(apps, schema_editor):
    QuestionBankBatch = apps.get_model('accounts', 'QuestionBankBatch')
    QuestionBankItem = apps.get_model('accounts', 'QuestionBankItem')
    batches = {}
    for item in QuestionBankItem.objects.filter(batch__isnull=True).order_by('id').iterator():
        exam_question = item.exam_questions.select_related('exam_set').order_by('id').first()
        name = exam_question.exam_set.title if exam_question else 'Earlier questions'
        key = (item.subject_id, exam_question.exam_set_id if exam_question else None)
        batch_id = batches.get(key)
        if batch_id is None:
            batch_id = QuestionBankBatch.objects.create(subject_id=item.subject_id, name=name).id
            batches[key] = batch_id
        QuestionBankItem.objects.filter(pk=item.pk).update(batch_id=batch_id)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0043_course_question_bank')]

    operations = [
        migrations.CreateModel(
            name='QuestionBankBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=160)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='question_batches', to='accounts.subject')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddField(
            model_name='questionbankitem',
            name='batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='accounts.questionbankbatch'),
        ),
        migrations.RunPython(group_existing_questions, migrations.RunPython.noop),
    ]
