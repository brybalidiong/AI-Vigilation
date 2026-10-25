import json

from django.db import migrations, models
import django.db.models.deletion


def copy_existing_questions(apps, schema_editor):
    ExamQuestion = apps.get_model('accounts', 'ExamQuestion')
    QuestionBankItem = apps.get_model('accounts', 'QuestionBankItem')
    existing = {}
    questions = ExamQuestion.objects.select_related('exam_set').order_by('id')
    for question in questions.iterator():
        signature = (
            question.exam_set.subject_id, question.question_type, question.question_text,
            json.dumps(question.choices, sort_keys=True), question.correct_answer,
            question.points, question.case_sensitive,
        )
        bank_id = existing.get(signature)
        if bank_id is None:
            bank = QuestionBankItem.objects.create(
                subject_id=question.exam_set.subject_id,
                question_type=question.question_type,
                question_text=question.question_text,
                choices=question.choices,
                correct_answer=question.correct_answer,
                points=question.points,
                case_sensitive=question.case_sensitive,
            )
            bank_id = bank.id
            existing[signature] = bank_id
        ExamQuestion.objects.filter(pk=question.pk).update(bank_item_id=bank_id)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0042_exam_backtracking')]

    operations = [
        migrations.CreateModel(
            name='QuestionBankItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_type', models.CharField(choices=[('multiple_choice', 'Multiple Choice'), ('identification', 'Identification'), ('enumeration', 'Enumeration'), ('essay', 'Essay')], max_length=20)),
                ('question_text', models.TextField()),
                ('choices', models.JSONField(blank=True, null=True)),
                ('correct_answer', models.CharField(blank=True, max_length=2000, null=True)),
                ('points', models.PositiveIntegerField(blank=True, null=True)),
                ('case_sensitive', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='question_bank', to='accounts.subject')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddField(
            model_name='examquestion',
            name='bank_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='exam_questions', to='accounts.questionbankitem'),
        ),
        migrations.RunPython(copy_existing_questions, migrations.RunPython.noop),
    ]
