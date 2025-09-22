import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from supabase_client import supabase_client

OUT_DIR = Path(os.getenv('EXPORT_DIR', 'data_export'))
BUCKET = os.getenv('SUPABASE_BUCKET')
PREFIX = os.getenv('SUPABASE_BUCKET_PREFIX') or ''


def main():
    if not supabase_client or not supabase_client.is_connected:
        print('ERROR: Supabase not connected. Check .env (SUPABASE_URL and keys).')
        raise SystemExit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # List all JSONs across the whole bucket root for full export
    paths = supabase_client.list_json_paths(bucket=BUCKET, prefix='', max_paths=None)
    print(f"Discovered {len(paths)} JSON files in bucket '{BUCKET}'. Exporting to '{OUT_DIR.resolve()}' ...")

    objs = supabase_client.download_jsons_concurrently(paths, bucket=BUCKET, max_workers=16)
    print(f"Downloaded {len(objs)} JSON objects; writing to disk...")

    written = 0
    for p, obj in zip(paths, objs):
        # Flatten any subfolders into names; keep folder structure under OUT_DIR
        out_path = OUT_DIR / p
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(obj, f, ensure_ascii=False)
            written += 1
        except Exception as e:
            print(f"FAILED to write {out_path}: {e}")

    print(f"Export complete. Wrote {written}/{len(paths)} files to {OUT_DIR}")


if __name__ == '__main__':
    main()
