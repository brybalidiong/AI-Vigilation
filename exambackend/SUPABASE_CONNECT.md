# Connect Django to Supabase

## 1. Check your network first

```powershell
cd exambackend
python manage.py diagnose_db
```

You need either:
- `Postgres SSLResponse=b'S'` (or `b'N'`), **or**
- `Django Connected — SELECT 1`

If you see **"TCP OK but server never answered Postgres handshake"**, your Wi‑Fi/firewall is blocking Postgres. **Code cannot fix this.** Use one of:

- Phone **mobile hotspot**
- Home network
- **VPN**
- Supabase **IPv4 add-on** (paid): https://supabase.com/dashboard/project/nxgxrsyboyvkhpmnkdwc/settings/addons

## 2. Get the connection string

1. Open https://supabase.com/dashboard/project/nxgxrsyboyvkhpmnkdwc
2. Click **Connect** (top) → **Session pooler** → **URI**
3. Copy the string (port **5432**)
4. Put it in `.env` as `DATABASE_URL=...` (replace password)

## 3. Run the backend

```powershell
python manage.py check_db
python manage.py runserver
```

## 4. Local SQLite fallback

Only if Supabase is unreachable:

```env
USE_LOCAL_SQLITE=1
```

This uses an empty local `db.sqlite3` — not your cloud data.
