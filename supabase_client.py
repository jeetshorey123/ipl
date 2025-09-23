"""
Automatic Supabase Client with Fallback Support
Automatically detects and uses Supabase if credentials are available
"""

import os
import json
import base64
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseClient:
    """
    Smart Supabase client that automatically detects configuration
    and falls back gracefully if Supabase is not available
    """
    
    def __init__(self):
        self.supabase = None
        self.is_connected = False
        # Storage config
        self.bucket_name: Optional[str] = None
        self.bucket_prefix: Optional[str] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client if credentials are available"""
        try:
            # Check for environment variables
            url = os.getenv("SUPABASE_URL")
            # Prefer service role key server-side (if provided), else anon
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
            
            # Also check for common alternative names
            if not url:
                url = os.getenv("SUPABASE_PROJECT_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
            if not key:
                key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
            # If URL is still missing but we have a JWT key, try to derive from 'ref' claim
            if not url and key:
                try:
                    parts = key.split('.')
                    if len(parts) >= 2:
                        payload_b64 = parts[1]
                        # Pad base64url
                        rem = len(payload_b64) % 4
                        if rem:
                            payload_b64 += '=' * (4 - rem)
                        payload_json = base64.urlsafe_b64decode(payload_b64.encode('utf-8')).decode('utf-8')
                        payload = json.loads(payload_json)
                        ref = payload.get('ref')
                        if ref and isinstance(ref, str):
                            # Clean any spaces just in case
                            ref = ref.strip().replace(' ', '')
                            url = f"https://{ref}.supabase.co"
                            os.environ['SUPABASE_URL'] = url
                            logger.info("Derived SUPABASE_URL from key payload: %s", url)
                except Exception as de:
                    logger.warning(f"Failed to derive SUPABASE_URL from key: {de}")
            
            if url and key:
                from supabase import create_client, Client
                self.supabase: Client = create_client(url, key)
                # Load storage-related env if present
                self.bucket_name = os.getenv("SUPABASE_BUCKET") or None
                # Normalize empty prefix to ''
                self.bucket_prefix = os.getenv("SUPABASE_BUCKET_PREFIX") or ''
                logger.info(
                    "Supabase env detected: url=%s, bucket=%s, prefix='%s', using_service_role=%s",
                    'set' if bool(url) else 'unset',
                    self.bucket_name or '(none)',
                    self.bucket_prefix,
                    bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
                )
                
                # Test connection
                self._test_connection()
                
                if self.is_connected:
                    logger.info("✅ Connected to Supabase successfully!")
                else:
                    logger.warning("❌ Supabase credentials found but connection failed")
            else:
                logger.warning(
                    "No Supabase credentials found. Please set SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY)."
                )
                
        except ImportError:
            logger.warning("Supabase library not installed - using local data")
        except Exception as e:
            logger.warning(f"Supabase connection failed: {str(e)} - using local data")
    
    def _test_connection(self):
        """Test if Supabase connection is working (table or storage)."""
        try:
            if not self.supabase:
                self.is_connected = False
                return
            # Prefer testing storage if bucket configured
            if self.bucket_name:
                try:
                    files = self.supabase.storage.from_(self.bucket_name).list(self.bucket_prefix or '')
                    # If list call succeeded, consider connected
                    self.is_connected = True
                    logger.info(f"Supabase Storage reachable; bucket='{self.bucket_name}', prefix='{self.bucket_prefix or ''}', found {len(files)} objects at top level")
                    return
                except Exception as se:
                    logger.warning(f"Supabase storage list failed: {se}")
            # Fallback: test table
            try:
                response = self.supabase.table('data').select("*").limit(1).execute()
                if response.data is not None:
                    self.is_connected = True
                    logger.info(f"Found {len(response.data)} sample records in Supabase 'data' table")
                    return
            except Exception as te:
                logger.warning(f"Supabase table test failed: {te}")
            # If both failed
            self.is_connected = False
        except Exception as e:
            logger.warning(f"Supabase connection test failed: {str(e)}")
            self.is_connected = False
    
    def get_all_matches(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all match data from Supabase
        Returns empty list if not connected
        """
        if not self.is_connected:
            return []
        
        try:
            query = self.supabase.table('data').select("*")
            
            if limit:
                query = query.limit(limit)
                
            response = query.execute()
            
            if response.data:
                logger.info(f"📊 Fetched {len(response.data)} matches from Supabase")
                return response.data
            else:
                logger.warning("No data found in Supabase 'data' table")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching data from Supabase: {str(e)}")
            return []

    def get_all_matches_from_bucket(self, bucket: Optional[str] = None, prefix: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch JSON match objects from a Supabase Storage bucket path.
        If bucket/prefix are omitted, uses configured env values.
        Returns list of parsed JSON objects (dicts).
        """
        if not self.is_connected or not self.supabase:
            return []
        bucket = bucket or self.bucket_name
        prefix = prefix if prefix is not None else (self.bucket_prefix or '')
        if not bucket:
            logger.warning("No bucket configured for Supabase storage fetch")
            return []
        try:
            storage = self.supabase.storage.from_(bucket)
            # List objects under the prefix; recursively list by traversing folders
            def crawl(start_prefix: str) -> List[str]:
                to_visit = [start_prefix]
                found: List[str] = []
                visited: set[str] = set()
                while to_visit:
                    raw_path = to_visit.pop(0)
                    # Normalize path: no leading slash, no trailing slash (except empty)
                    path = (raw_path or '').strip('/')
                    if path in visited:
                        continue
                    visited.add(path)
                    # storage.list expects folder path without leading slash; '' means root
                    list_path = path if path else ''
                    items = storage.list(list_path)
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        name = it.get('name')
                        if not name:
                            continue
                        full_path = f"{path}/{name}" if path else name
                        meta = it.get('metadata') or {}
                        mimetype = meta.get('mimetype') or meta.get('contentType')
                        is_file = bool(mimetype) or ('.' in name)
                        if is_file:
                            mimetype_str = (str(mimetype).lower() if mimetype else '')
                            if name.lower().endswith('.json') or ('json' in mimetype_str):
                                found.append(full_path)
                        else:
                            to_visit.append(full_path)
                return found

            files: List[str] = crawl(prefix)
            # If nothing found at provided prefix, try a set of fallbacks (toggle trailing slash, root, and common prefixes)
            if not files:
                fallbacks = []
                # Toggle trailing slash variants of the provided prefix
                if prefix:
                    p = prefix.rstrip('/')
                    if p:
                        fallbacks.extend([p, f"{p}/"])  # normalized and with slash
                # Always try from root
                fallbacks.append('')
                # Try common folder names
                fallbacks.extend(['data', 'data/', 'matches', 'matches/', 'json', 'json/', '2024', '2024/', 'dataset', 'dataset/', 'datasets', 'datasets/'])

                tried = set([prefix])
                for cand in fallbacks:
                    if cand in tried:
                        continue
                    tried.add(cand)
                    try:
                        cfiles = crawl(cand)
                        if cfiles:
                            files = cfiles
                            # Update discovered working prefix for future calls
                            self.bucket_prefix = cand
                            logger.info("Discovered JSON files under prefix '%s'", cand)
                            break
                    except Exception:
                        continue
            if limit:
                files = files[:limit]
            matches: List[Dict[str, Any]] = []
            for fp in files:
                try:
                    data_bytes = storage.download(fp)
                    text = data_bytes.decode('utf-8') if isinstance(data_bytes, (bytes, bytearray)) else str(data_bytes)
                    obj = json.loads(text)
                    matches.append(obj)
                except Exception as de:
                    logger.warning(f"Failed to download/parse '{fp}': {de}")
                    continue
            logger.info(f"📦 Fetched {len(matches)} JSON objects from bucket '{bucket}' with prefix '{prefix}'")
            return matches
        except Exception as e:
            logger.error(f"Error fetching from Supabase Storage: {e}")
            return []

    def list_json_paths(self, bucket: Optional[str] = None, prefix: Optional[str] = None, max_paths: Optional[int] = None) -> List[str]:
        """List all JSON file paths under a bucket/prefix recursively without downloading contents.
        Includes pagination so folders with >100 items are fully traversed.
        """
        if not self.is_connected or not self.supabase:
            return []
        bucket = bucket or self.bucket_name
        prefix = prefix if prefix is not None else (self.bucket_prefix or '')
        if not bucket:
            return []
        storage = self.supabase.storage.from_(bucket)

        def list_dir_paged(dir_path: str) -> List[Dict[str, Any]]:
            """List a directory handling pagination (limit/offset)."""
            all_items: List[Dict[str, Any]] = []
            limit = 100
            offset = 0
            while True:
                try:
                    items = storage.list(dir_path, {"limit": limit, "offset": offset})
                except Exception:
                    items = []
                if not items:
                    break
                all_items.extend(items)
                if len(items) < limit:
                    break
                offset += limit
            return all_items

        def crawl(start_prefix: str) -> List[str]:
            to_visit = [start_prefix]
            found: List[str] = []
            visited: set[str] = set()
            while to_visit:
                raw_path = to_visit.pop(0)
                path = (raw_path or '').strip('/')
                if path in visited:
                    continue
                visited.add(path)
                items = list_dir_paged(path if path else '')
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    name = it.get('name')
                    if not name:
                        continue
                    full_path = f"{path}/{name}" if path else name
                    meta = it.get('metadata') or {}
                    mimetype = meta.get('mimetype') or meta.get('contentType')
                    is_file = bool(mimetype) or ('.' in name)
                    if is_file:
                        mimetype_str = (str(mimetype).lower() if mimetype else '')
                        if name.lower().endswith('.json') or ('json' in mimetype_str):
                            found.append(full_path)
                        if max_paths and len(found) >= max_paths:
                            return found
                    elif not is_file:
                        to_visit.append(full_path)
            return found

        files = crawl(prefix)
        if not files:
            # Try common fallbacks
            for cand in ['', 'data', 'matches', 'json']:
                files = crawl(cand)
                if files:
                    self.bucket_prefix = cand
                    break
        return files[:max_paths] if max_paths else files

    def download_jsons_concurrently(self, file_paths: List[str], bucket: Optional[str] = None, max_workers: int = 12):
        """Download and parse many JSON files concurrently for speed.
        Returns a list of (path, object) tuples for accurate mapping.
        """
        if not self.is_connected or not self.supabase or not file_paths:
            return []
        bucket = bucket or self.bucket_name
        if not bucket:
            return []
        results: List[tuple[str, Dict[str, Any]]] = []
        storage = self.supabase.storage.from_(bucket)

        def fetch(path: str):
            attempts = 5
            backoff = 0.2
            for attempt in range(attempts):
                try:
                    data_bytes = storage.download(path)
                    text = data_bytes.decode('utf-8') if isinstance(data_bytes, (bytes, bytearray)) else str(data_bytes)
                    return path, json.loads(text)
                except Exception as e:
                    msg = str(e) if e else ''
                    # Treat Windows non-blocking socket error 10035 and similar as transient
                    transient = ('10035' in msg) or ('non-blocking socket operation' in msg.lower())
                    if attempt < attempts - 1 and transient:
                        import time
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 2.0)
                        continue
                    raise

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(fetch, p): p for p in file_paths}
            for fut in as_completed(future_map):
                try:
                    path, obj = fut.result()
                    if isinstance(obj, dict):
                        results.append((path, obj))
                except Exception as de:
                    path = future_map[fut]
                    logger.warning(f"Failed to download/parse '{path}': {de}")
                    continue
        logger.info(f"⬇️  Concurrently fetched {len(results)} JSON objects from bucket '{bucket}'")
        return results

    # Backward-compatible alias expected by data_processor
    def list_json_files(self, bucket: Optional[str] = None, prefix: Optional[str] = None, max_files: Optional[int] = None) -> List[str]:
        return self.list_json_paths(bucket=bucket, prefix=prefix, max_paths=max_files)
    
    def get_matches_by_filter(self, **filters) -> List[Dict[str, Any]]:
        """
        Get matches with specific filters
        Common filters: team, venue, season, match_type
        """
        if not self.is_connected:
            return []
        
        try:
            query = self.supabase.table('data').select("*")
            
            # Apply filters dynamically
            for key, value in filters.items():
                if value is not None:
                    # Handle different filter types
                    if key == 'teams':
                        # Filter by team (assumes team info is in JSON structure)
                        query = query.or_(f'team1.eq.{value},team2.eq.{value}')
                    elif key == 'season':
                        # Filter by season/year
                        query = query.eq('season', value)
                    else:
                        # Generic equality filter
                        query = query.eq(key, value)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error filtering Supabase data: {str(e)}")
            return []

    # Removed duplicate definition of list_json_files (use alias above that calls list_json_paths)
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get information about the data table structure"""
        if not self.is_connected:
            return {"connected": False, "message": "Not connected to Supabase"}
        
        try:
            # Get sample record to understand structure
            response = self.supabase.table('data').select("*").limit(1).execute()
            
            if response.data:
                sample = response.data[0]
                return {
                    "connected": True,
                    "table_exists": True,
                    "sample_keys": list(sample.keys()) if isinstance(sample, dict) else [],
                    "record_count": "Available"
                }
            else:
                return {
                    "connected": True,
                    "table_exists": True,
                    "sample_keys": [],
                    "record_count": 0
                }
                
        except Exception as e:
            return {
                "connected": True,
                "table_exists": False,
                "error": str(e)
            }

# Global instance - automatically initialized
supabase_client = SupabaseClient()

def get_supabase_status() -> Dict[str, Any]:
    """Get current Supabase connection status"""
    status = {
        "connected": supabase_client.is_connected,
        "client_available": supabase_client.supabase is not None,
        "table_info": supabase_client.get_table_info()
    }
    # Include storage config summary
    status["storage"] = {
        "bucket": supabase_client.bucket_name,
        "prefix": supabase_client.bucket_prefix,
        "configured": supabase_client.bucket_name is not None
    }
    return status