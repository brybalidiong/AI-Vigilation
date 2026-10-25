from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0044_question_bank_batches')]

    operations = [
        migrations.AddField(
            model_name='examquestion',
            name='max_words',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='questionbankitem',
            name='max_words',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
