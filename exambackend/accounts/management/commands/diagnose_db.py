"""Network + database diagnostics for Supabase (run: python manage.py diagnose_db)."""
import socket
import struct
import time

from django.conf import settings
from django.core.management.base import BaseCommand


def _probe_postgres(host: str, port: int, timeout: float = 5.0) -> str:
    try:
        t0 = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        tcp_ms = int((time.time() - t0) * 1000)
        sock.settimeout(timeout)
        sock.sendall(struct.pack('!II', 8, 80877103))  # PostgreSQL SSLRequest
        try:
            resp = sock.recv(1)
            sock.close()
            return f'TCP OK ({tcp_ms}ms), Postgres SSLResponse={resp!r}'
        except OSError:
            sock.close()
            return (
                f'TCP OK ({tcp_ms}ms) but server never answered Postgres handshake — '
                'your network is blocking database traffic (try mobile hotspot or home Wi-Fi).'
            )
    except OSError as exc:
        return f'Failed: {exc}'


class Command(BaseCommand):
    help = 'Diagnose Supabase / Postgres connectivity (network + Django).'

    def handle(self, *args, **options):
        pooler = 'aws-1-ap-northeast-1.pooler.supabase.com'
        direct = 'db.nxgxrsyboyvkhpmnkdwc.supabase.co'

        self.stdout.write('=== Supabase connectivity ===')
        ipv4: list[str] = []
        try:
            infos = socket.getaddrinfo(pooler, 5432, proto=socket.IPPROTO_TCP)
            ipv4 = sorted({i[4][0] for i in infos if i[0] == socket.AF_INET})
            self.stdout.write(f'Pooler IPv4: {", ".join(ipv4) or "none"}')
        except OSError as exc:
            self.stdout.write(f'Pooler DNS failed: {exc}')

        try:
            infos6 = socket.getaddrinfo(direct, 5432, proto=socket.IPPROTO_TCP)
            has_v6 = any(i[0] == socket.AF_INET6 for i in infos6)
            has_v4 = any(i[0] == socket.AF_INET for i in infos6)
            self.stdout.write(f'Direct host {direct}: IPv4={has_v4}, IPv6={has_v6}')
            if has_v6 and not has_v4:
                self.stdout.write(
                    self.style.WARNING(
                        'Direct connection is IPv6-only. Enable Supabase IPv4 add-on or IPv6 on your PC.'
                    )
                )
        except OSError as exc:
            self.stdout.write(f'Direct DNS failed: {exc}')

        if ipv4:
            self.stdout.write(f'Probe {ipv4[0]}:5432 -> {_probe_postgres(ipv4[0], 5432)}')
        self.stdout.write(f'Probe {pooler}:5432 -> {_probe_postgres(pooler, 5432)}')

        self.stdout.write('')
        self.stdout.write('=== Django database config ===')
        db = settings.DATABASES['default']
        if 'sqlite' in db.get('ENGINE', ''):
            self.stdout.write(self.style.WARNING(f'USE_LOCAL_SQLITE is ON — using {db.get("NAME")}'))
            self.stdout.write('Set USE_LOCAL_SQLITE=0 in .env when Supabase probe above shows SSLResponse.')
            return

        self.stdout.write(f'Engine: {db.get("ENGINE")}')
        self.stdout.write(f'Host: {db.get("HOST")}:{db.get("PORT")}  User: {db.get("USER")}')

        from django.db import connection

        self.stdout.write('Django connect...')
        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                row = cursor.fetchone()
            self.stdout.write(self.style.SUCCESS(f'Connected - SELECT 1 => {row}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Django connection failed: {exc}'))

        self.stdout.write('')
        self.stdout.write('Fix checklist:')
        self.stdout.write('  1. Supabase dashboard - project must be Active (not paused).')
        self.stdout.write('  2. Settings - Database - reset password - update DATABASE_URL in .env')
        self.stdout.write('  3. Use Session pooler URI (port 5432).')
        self.stdout.write('  4. If probe shows Postgres handshake timeout: use mobile hotspot / home network.')
        self.stdout.write('  5. Or enable Supabase IPv4 add-on for direct IPv4 access.')
