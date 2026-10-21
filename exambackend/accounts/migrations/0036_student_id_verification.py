from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0035_move_admin_credentials_to_database')]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='id_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
