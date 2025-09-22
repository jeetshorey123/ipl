import os
from dotenv import load_dotenv

load_dotenv()
print("ENV CHECK:")
print("  SUPABASE_URL set?", bool(os.getenv('SUPABASE_URL')))
print("  Using service role?", bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY')))
print("  Bucket:", os.getenv('SUPABASE_BUCKET'))
print("  Prefix:", os.getenv('SUPABASE_BUCKET_PREFIX'))

from supabase_client import supabase_client

print("Connected:", supabase_client.is_connected)
print("Bucket:", supabase_client.bucket_name)
print("Prefix:", supabase_client.bucket_prefix)

if not supabase_client.is_connected:
    print("Not connected. Check SUPABASE_URL and key in .env.")
    raise SystemExit(1)

if not supabase_client.bucket_name:
    print("No SUPABASE_BUCKET configured in .env")
    raise SystemExit(1)

rows = supabase_client.get_all_matches_from_bucket(limit=5)
print("Fetched from bucket:", len(rows))

if rows:
    sample = rows[0]
    print("Sample keys:", list(sample.keys())[:10] if isinstance(sample, dict) else type(sample))
else:
    print("No JSON files found at the given bucket/prefix or access denied.")
