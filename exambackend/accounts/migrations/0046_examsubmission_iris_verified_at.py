from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0045_essay_max_words')]

    operations = [
        migrations.AddField(
            model_name='examsubmission',
            name='iris_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
