"""Test database connectivity (run: python manage.py check_db)."""
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Verify database connection settings and run SELECT 1.'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        engine = db.get('ENGINE', '')
        self.stdout.write(f'Engine: {engine}')
        if 'sqlite' in engine:
            self.stdout.write(self.style.SUCCESS(f'SQLite: {db.get("NAME")}'))
            return

        host = db.get('HOST')
        port = db.get('PORT')
        user = db.get('USER')
        timeout = db.get('OPTIONS', {}).get('connect_timeout', 20)
        self.stdout.write(f'Host: {host}:{port}  User: {user}')
        self.stdout.write(f'SSL: {db.get("OPTIONS", {}).get("sslmode")}  Timeout: {timeout}s')
        self.stdout.write('Connecting… (Ctrl+C if this hangs — your network may block Postgres)')

        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                row = cursor.fetchone()
            self.stdout.write(self.style.SUCCESS(f'Connected — SELECT 1 => {row}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Connection failed: {exc}'))
            self.stdout.write(
                'Tips: In Supabase → Project Settings → Database, copy the '
                'Session pooler URI (port 5432). Paste as DATABASE_URL in .env. '
                'If on school/corporate Wi-Fi, try mobile hotspot or set USE_LOCAL_SQLITE=1.'
            )
