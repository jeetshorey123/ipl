# Supabase Storage Setup for Cricket Analytics

1) Create `.env` from template

Copy `.env.example` to `.env` and fill:

```
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_BUCKET=<bucket-name>
SUPABASE_BUCKET_PREFIX=<optional/subfolder>
```

2) Ensure bucket contains match JSONs

- Place `.json` files that contain objects with `info` and `innings` keys.
- If nested in folders, set `SUPABASE_BUCKET_PREFIX` to that folder (do not start with slash).

3) Bucket access policy

- Easiest: make bucket public.
- Or add a Storage policy to allow listing and downloading for anon role.

Example policy:

```sql
create policy "Allow public read" on storage.objects
for select using (bucket_id = '<bucket-name>');
```

4) Run app

```powershell
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

5) Verify

- GET `http://127.0.0.1:5000/api/supabase/status`
- GET `http://127.0.0.1:5000/api/supabase/sample`
- GET `http://127.0.0.1:5000/api/data/health`

You should see `connected: true`, `storage.configured: true`, and non-zero `matches_loaded`.
