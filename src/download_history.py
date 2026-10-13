"""Fetch immutable, checksummed public training inputs; no private credentials."""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.request

from runtime import workspace_root
ROOT = workspace_root()

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "personal-fpl-research/1.0"})
    return urllib.request.urlopen(req, timeout=90).read()

def main():
    root = ROOT / "data" / "historical"
    root.mkdir(parents=True, exist_ok=True)
    if (root/'manifest.json').exists():
        manifest=json.loads((root/'manifest.json').read_text())
        for item in manifest['files']:
            if 'error' in item:raise ValueError('Incomplete existing download; review before replacing manifest')
            assert hashlib.sha256((root/item['season']/item['file']).read_bytes()).hexdigest()==item['sha256']
        print('Existing immutable historical download verified; nothing overwritten.')
        return
    commit = json.loads(get("https://api.github.com/repos/vaastav/Fantasy-Premier-League/commits/master"))["sha"]
    def fetch(item):
        season, name = item
        url = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{commit}/data/{season}/{name}"
        path = root / season / name
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = get(url)
            path.write_bytes(data)
            return {"season": season, "file": name, "url": url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        except Exception as e:
            return {"season": season, "file": name, "url": url, "error": str(e)}
    jobs = [(s, f) for s in ["2020-21","2021-22","2022-23","2023-24","2024-25","2025-26"] for f in ["gws/merged_gw.csv", "players_raw.csv", "teams.csv"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(fetch,jobs))
    (root / "manifest.json").write_text(json.dumps({"commit":commit,"files":result}, indent=2)+"\n")
    for r in result:
        print(r["season"], r["file"], r.get("bytes", r.get("error")), flush=True)

if __name__ == "__main__":
    main()
