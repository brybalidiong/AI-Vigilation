from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0033_examset_detect_gadgets'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='institute',
            field=models.CharField(
                blank=True,
                choices=[
                    ('IC', 'Institute of Computing'),
                    ('ITED', 'Institute of Teachers Education'),
                    ('IASS', 'Institute of Acquatic and Applied Sciences'),
                    ('ILEGG', 'Institute of Leadership, Entrepreneurship and Good Governance'),
                ],
                default='',
                max_length=5,
            ),
        ),
    ]
