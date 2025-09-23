# Cricket Analytics (Supabase-only)

This app loads cricket JSON match data exclusively from Supabase Storage in the background and serves analytics via Flask.

## Run

1. Create `.env` with Supabase credentials:

```
SUPABASE_URL=... 
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_BUCKET=ipl
SUPABASE_BUCKET_PREFIX=data/
# Optional: limit files on startup
SUPABASE_MAX_FILES=5
```

2. Start the server:

```
python app.py
```

The app will start a background loader from Supabase Storage. No local JSONs are read.

Notes:
- Local data mode is disabled by default; code paths read from Supabase only.
- Health endpoint: `/api/data/health` shows loading progress.
