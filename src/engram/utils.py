import os
import time
import json
import hashlib
import tempfile
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any

def download_asset_foolproof(url: str, dest_path: str, expected_sha256: str = None, max_retries: int = 3) -> Path:
    """
    Downloads a large file atomically with SHA256 validation and exponential backoff.
    Standard library only. Zero dependencies.
    """
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Fast-path: Check if valid file already exists
    if dest.exists() and expected_sha256:
        file_hash = hashlib.sha256()
        with open(dest, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                file_hash.update(chunk)
        if file_hash.hexdigest().lower() == expected_sha256.lower():
            return dest

    tmp_dest = dest.with_suffix('.tmp')
    delay = 1.0
    
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=30) as response:
                sha256_hash = hashlib.sha256()
                
                with open(tmp_dest, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        sha256_hash.update(chunk)
                        
            # Validation
            if expected_sha256:
                actual_hash = sha256_hash.hexdigest()
                if actual_hash.lower() != expected_sha256.lower():
                    raise ValueError(f"Checksum mismatch. Expected {expected_sha256}, got {actual_hash}")
                
            # Atomicity: Rename tmp file to final destination
            os.replace(tmp_dest, dest)
            return dest
            
        except (urllib.error.URLError, OSError, ValueError) as e:
            if tmp_dest.exists():
                tmp_dest.unlink()
                
            if attempt == max_retries:
                raise RuntimeError(f"Failed to download asset after {max_retries} attempts: {e}")
                
            time.sleep(delay)
            delay *= 2

    return dest

def foolproof_update_json(config_path_str: str, updater_func) -> None:
    """
    Atomically updates a JSON file (like claude_desktop_config.json) safely.
    `updater_func` takes the parsed dictionary and modifies it in-place.
    """
    config_path = Path(config_path_str)
    
    # 1. ROBUST PARSING
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Existing config is malformed JSON. Aborting. Error: {e}")
    else:
        config_data = {}

    # Update logic
    updater_func(config_data)

    # 2. BACKUP GENERATION
    if config_path.exists():
        backup_path = config_path.with_suffix('.json.bak')
        shutil.copy2(config_path, backup_path) 

    # 3. ATOMIC WRITE
    target_dir = config_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    
    with tempfile.NamedTemporaryFile('w', dir=target_dir, delete=False, encoding='utf-8') as tf:
        json.dump(config_data, tf, indent=2)
        tf.flush()
        os.fsync(tf.fileno())
        temp_name = tf.name

    try:
        os.replace(temp_name, config_path)
    except Exception as e:
        os.remove(temp_name)
        raise e

import functools

def retry_db_lock(max_retries=7):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = 0.1
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "database is locked" in str(e).lower():
                        if attempt == max_retries:
                            raise e
                        time.sleep(delay)
                        delay = min(delay * 2, 5.0)
                    else:
                        raise e
        return wrapper
    return decorator
