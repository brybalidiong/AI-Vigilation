from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0032_add_gadget_detection_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='examset',
            name='detect_gadgets',
            field=models.BooleanField(default=True),
        ),
    ]
