"""Copy the existing deployment admin secret into Django's password hash table once."""

import os

from django.contrib.auth.hashers import make_password
from django.db import migrations


def move_admin_credentials(apps, schema_editor):
    password = os.getenv('ADMIN_PASSWORD', '').strip()
    if not password:
        return

    username = os.getenv('ADMIN_USERNAME', 'admin').strip() or 'admin'
    alias = schema_editor.connection.alias
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('accounts', 'UserProfile')

    admin_user = User.objects.using(alias).filter(username=username).first()
    if admin_user:
        if not admin_user.is_staff or not admin_user.is_superuser:
            raise RuntimeError('The configured admin username belongs to a non-admin account.')
        profile = UserProfile.objects.using(alias).filter(user_id=admin_user.pk).first()
        if profile and profile.role != 'admin':
            raise RuntimeError('The configured admin username has a non-admin profile.')
        admin_user.password = make_password(password)
        admin_user.save(using=alias, update_fields=['password'])
    else:
        admin_user = User.objects.using(alias).create(
            username=username,
            password=make_password(password),
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

    UserProfile.objects.using(alias).get_or_create(
        user_id=admin_user.pk,
        defaults={'role': 'admin', 'is_enrolled': False},
    )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0034_userprofile_institute'),
    ]

    operations = [
        migrations.RunPython(move_admin_credentials, migrations.RunPython.noop),
    ]
