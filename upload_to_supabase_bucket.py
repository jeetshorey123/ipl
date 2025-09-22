import os
import glob
from dotenv import load_dotenv

load_dotenv()

from supabase_client import supabase_client

BUCKET = os.getenv('SUPABASE_BUCKET')
PREFIX = os.getenv('SUPABASE_BUCKET_PREFIX') or ''
LOCAL_DIR = os.path.join(os.path.dirname(__file__), 'data')
LIMIT = int(os.getenv('UPLOAD_LIMIT', '25'))  # upload a small sample by default

if not supabase_client.is_connected:
    print('ERROR: Not connected to Supabase. Check SUPABASE_URL and key in .env')
    raise SystemExit(1)

if not BUCKET:
    print('ERROR: SUPABASE_BUCKET not set in .env')
    raise SystemExit(1)

if not os.path.isdir(LOCAL_DIR):
    print(f'ERROR: Local data directory not found: {LOCAL_DIR}')
    raise SystemExit(1)

storage = supabase_client.supabase.storage.from_(BUCKET)

files = glob.glob(os.path.join(LOCAL_DIR, '*.json'))
files.sort()
if LIMIT > 0:
    files = files[:LIMIT]
print(f'Found {len(files)} local JSON files to upload to bucket {BUCKET}/{PREFIX}')

uploaded = 0
failed = 0
for fp in files:
    name = os.path.basename(fp)
    remote_path = f"{PREFIX}/{name}" if PREFIX else name
    try:
        with open(fp, 'rb') as f:
            content = f.read()
        # upsert must be a string 'true' per http headers expectations in supabase-py
        res = storage.upload(remote_path, content, {
            'contentType': 'application/json',
            'upsert': 'true',
            'cacheControl': '3600'
        })
        uploaded += 1
        print(f'Uploaded: {remote_path}')
    except Exception as e:
        failed += 1
        print(f'FAILED: {remote_path} -> {e}')

print(f'Upload complete. Success: {uploaded}, Failed: {failed}')
