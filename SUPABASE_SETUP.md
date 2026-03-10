# Using Supabase as Your Database

Your backend can use **Supabase** (PostgreSQL) instead of MySQL. No code changes are required beyond configuration.

## 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and sign in.
2. **New project** → choose organization, name, database password, and region.
3. Wait for the project to be ready.

## 2. Get the connection string

1. In the Supabase dashboard, open **Project Settings** (gear) → **Database**.
2. Under **Connection string**, choose:
   - **URI** (recommended for this app).
   - **Session mode** (port **5432**) for a long-running server, or **Transaction mode** (port **6543**) for serverless / many short-lived connections.
3. Copy the URI. It looks like:
   - Direct: `postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:5432/postgres`
   - Or: `postgresql://postgres:[YOUR-PASSWORD]@db.[project-ref].supabase.co:5432/postgres`
4. Replace `[YOUR-PASSWORD]` with your **database password** (the one you set when creating the project).  
   If the password contains special characters, URL-encode them (e.g. `@` → `%40`, `#` → `%23`).

## 3. Configure the backend

In your backend root (e.g. `backend/`), create or edit `.env`:

```env
# Supabase PostgreSQL (replace with your actual URI and password)
DATABASE_URL=postgresql://postgres.[project-ref]:YOUR_PASSWORD@aws-0-[region].pooler.supabase.com:5432/postgres

# Only if you use Transaction mode (port 6543) / serverless
# USE_SUPABASE_POOLER=true
```

- Use the **Session mode** (5432) URI for a normal FastAPI server.
- If you use the **Transaction mode** (6543) URI, either set `USE_SUPABASE_POOLER=true` or the app will detect `pooler.supabase.com` and use connection settings suited for the pooler.

Remove or comment out any previous `DATABASE_URL` that pointed to MySQL so Supabase is used.

## 4. Install dependencies

From the backend folder:

```bash
pip install -r requirements.txt
```

This installs `psycopg2-binary` (PostgreSQL driver) in addition to your existing dependencies.

## 5. Create tables

On first run, the app creates tables from your SQLAlchemy models:

```bash
cd backend
uvicorn app.main:app --reload
```

Alternatively, run once and exit so that `Base.metadata.create_all(bind=engine)` in `main.py` runs and creates tables in Supabase.

Tables created:

- `users`
- `orders`
- `attendance`
- `payroll`
- `inventory`
- `ai_image_log`

## 6. (Optional) Seed an admin user

If you use a seed script (e.g. `seed_admin.py`), run it after tables exist:

```bash
python seed_admin.py
```

Use the same `.env` so `DATABASE_URL` points to Supabase.

## 7. Migrating existing data from MySQL

If you already have data in MySQL:

1. **Option A – Export/import**
   - Export from MySQL (e.g. `mysqldump` or CSV).
   - Map tables/columns to the Supabase (PostgreSQL) schema.
   - Import via Supabase SQL Editor, `psql`, or a small script using your ORM.

2. **Option B – ETL script**
   - Use a one-off script that reads from MySQL and writes to the Supabase DB using the same SQLAlchemy models and `DATABASE_URL` pointing to Supabase.

3. **Option C – Fresh start**
   - Point `DATABASE_URL` at Supabase, start the app (tables created), then re-create users and data manually or via your seed/scripts.

## Troubleshooting

- **Connection refused / timeout**
  - Check Supabase **Database** settings for the correct host, port (5432 or 6543), and “Use connection pooling” (Session vs Transaction).
  - Ensure your IP is allowed if Supabase has network restrictions (e.g. in **Database** → **Network**).

- **Authentication failed**
  - Confirm the password in `DATABASE_URL` is the **database** password (not the dashboard login).
  - URL-encode any special characters in the password.

- **SSL**
  - Supabase often requires SSL. If you see SSL-related errors, add `?sslmode=require` to the end of `DATABASE_URL` (or the parameter your driver expects).

- **Too many connections**
  - For Transaction mode / pooler, set `USE_SUPABASE_POOLER=true` so the app uses a pooler-friendly configuration (e.g. NullPool).

Your app code does not need to change: only `DATABASE_URL` (and optionally `USE_SUPABASE_POOLER`) in `.env` and installing the new dependency.