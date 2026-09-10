#!/usr/bin/env python3
"""PREDATOR — publication automatique GitHub Pages (stats réelles + statut).
Usage: python publish_stats.py [repo] [token via env GH_TOKEN]
Lit predator_ultra.db (lecture seule), met à jour STATUS.json/DATASET_STATS.json/README,
pousse vers iservice49800-ops/PREDATOR-docs via l'API REST (curl-free, urllib).
"""
import base64, datetime, json, os, sqlite3, sys, urllib.request

REPO = "iservice49800-ops/PREDATOR-docs"
PAGES = "https://iservice49800-ops.github.io/PREDATOR-docs"
DB = r"C:/Users/Deziz/PREDATOR/predator_ultra.db"
GH = os.environ.get("GH_TOKEN", "")

def gh_get(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/contents/{path}",
                                 headers={"Authorization": f"Bearer {GH}", "Accept": "application/vnd.github+json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except Exception:
        return None

def gh_put(path, content, msg, sha=None):
    data = {"message": msg, "content": base64.b64encode(content.encode()).decode()}
    if sha: data["sha"] = sha
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/contents/{path}",
                                 data=json.dumps(data).encode(),
                                 headers={"Authorization": f"Bearer {GH}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json"}, method="PUT")
    return json.load(urllib.request.urlopen(req, timeout=30))

def collect_stats():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cols = [r[1] for r in con.execute("PRAGMA table_info(items)").fetchall()]
    stats = {"total_items": 0, "domains": {}, "sources": {}}
    try: stats["total_items"] = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    except Exception as e: print("count err:", e)
    if "domain" in cols:
        for d, c in con.execute("SELECT domain, COUNT(*) FROM items GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 30"): stats["domains"][d] = c
    if "source" in cols:
        for s, c in con.execute("SELECT source, COUNT(*) FROM items GROUP BY source ORDER BY COUNT(*) DESC LIMIT 30"): stats["sources"][s] = c
    con.close()
    stats["domains_count"] = len(stats["domains"]); stats["sources_count"] = len(stats["sources"])
    stats["goal"] = 3000000; stats["progress_pct"] = round(stats["total_items"] / 3_000_000 * 100, 2)
    stats["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return stats

def main():
    stats = collect_stats()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status = {"service": "PREDATOR", "version": "2.0.0", "status": "operational", "updated_at": now,
              "datasets": {"total_items": stats["total_items"], "goal": stats["goal"],
                           "progress_pct": stats["progress_pct"],
                           "domains": list(stats["domains"].keys())[:12],
                           "sources": list(stats["sources"].keys())[:12]},
              "rails": ["x402 USDC Base", "Lightning L402 Coinos", "CCTP"],
              "marketplaces": ["AgentBazaar", "AgenticTrade", "AgorAgentic", "ClawMerchants", "Vertical Marketplace", "Nevermined"]}
    files = [
        ("STATUS.json", json.dumps(status, indent=2), f"Auto-publish stats {stats['total_items']:,} items ({stats['progress_pct']}% of 3M)"),
        ("DATASET_STATS.json", json.dumps(stats, indent=2), f"Auto-publish dataset stats {stats['total_items']:,}"),
    ]
    ok = 0
    for path, content, msg in files:
        try:
            existing = gh_get(path)
            sha = existing.get("sha") if existing else None
            gh_put(path, content, msg, sha)
            print(f"✅ {path} ({stats['total_items']:,} items)")
            ok += 1
        except Exception as e:
            print(f"❌ {path}: {e}")
    print(f"→ {ok}/{len(files)} pushed. Page: {PAGES}/STATUS.json")

if __name__ == "__main__":
    main()