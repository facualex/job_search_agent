"""
Estado persistente simple: qué ofertas (por URL) ya fueron mostradas antes,
para no repetirlas día a día. Se guarda como JSON y se commitea de vuelta
al repo desde el workflow de GitHub Actions.
"""
import json
import os
import time
from config import SEEN_JOBS_FILE, SEEN_JOBS_MAX_AGE_DAYS


def load_seen():
    if not os.path.exists(SEEN_JOBS_FILE):
        return {}
    try:
        with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[state] WARNING: no se pudo leer {SEEN_JOBS_FILE}: {e}")
        return {}


def save_seen(seen: dict):
    # Limpieza: descarta entradas más viejas que SEEN_JOBS_MAX_AGE_DAYS
    cutoff = time.time() - SEEN_JOBS_MAX_AGE_DAYS * 86400
    cleaned = {url: ts for url, ts in seen.items() if ts >= cutoff}
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)


def filter_unseen(jobs: list, seen: dict) -> list:
    return [j for j in jobs if j["url"] not in seen]


def mark_seen(jobs: list, seen: dict):
    now = time.time()
    for j in jobs:
        seen[j["url"]] = now
