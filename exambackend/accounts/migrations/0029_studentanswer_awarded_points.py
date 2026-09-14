from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0028_add_case_sensitive_and_expand_correct_answer'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentanswer',
            name='awarded_points',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=7,
                null=True,
            ),
        ),
    ]
