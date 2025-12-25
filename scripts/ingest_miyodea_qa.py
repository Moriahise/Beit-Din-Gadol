"""
Modified MiYodea Q&A ingest script.

This script reads MiYodea Q&A dumps from the `miyodea/qa` directory and
merges them into the existing `qa_db.json` without overwriting Yeshiva
entries. It also surfaces each question's original URL as a top‑level
`url` field (pulled from `metadata.url` when present) so that the
front‑end can display a proper source link. New entries are added to
`responsa.json` for indexing.

To use this script, run it from the repository root. It will read
existing `qa_db.json` and `responsa.json` if they exist, merge in new
MiYodea items, and write the updated files back to disk.
"""

import json
import glob
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))  # repo root
RESPONSA_PATH = os.path.join(ROOT, "responsa.json")
QA_DB_PATH = os.path.join(ROOT, "qa_db.json")
MIYODEA_GLOB = os.path.join(ROOT, "miyodea", "qa", "*.json")

def load_json(path, default):
    """Load a JSON file and return a default value on failure."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        # Log parse error and return default to avoid breaking ingest
        print(f"⚠️  Failed to parse {path}: {exc}")
        return default

def save_json(path, data):
    """Save a Python object as JSON with UTF‑8 encoding."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_summary_from_content(content: str) -> str:
    """Return the first ~220 characters of the content as a summary."""
    s = (content or "").replace("\n", " ").strip()
    return (s[:220] + "…") if len(s) > 220 else s

def extract_year(meta_date: str) -> int:
    """Extract the year component from an ISO date string."""
    if not meta_date:
        return datetime.utcnow().year
    try:
        return int(meta_date[:4])
    except Exception:
        return datetime.utcnow().year

def to_responsa_entry(item, src_relpath: str):
    """Build a responsa entry from a MiYodea question item."""
    meta = item.get("metadata", {}) or {}
    qid = str(item.get("id", "")).strip()

    # number: try to use digits from id, else fallback hash-ish
    digits = "".join(ch for ch in qid if ch.isdigit())
    number = int(digits) if digits else 0

    year = extract_year(meta.get("date"))
    if meta.get("date"):
        date_str = meta["date"][:10]  # YYYY-MM-DD
    else:
        date_str = f"{year}-01-01"

    title = item.get("title") or f"Q&A {qid}"
    summary = normalize_summary_from_content(item.get("content", ""))

    return {
        "number": number,
        "title_he": title,   # MiYodea is mostly EN; keep same
        "title_en": title,
        "summary_he": summary,
        "summary_en": summary,
        "category": "other",
        "category_he": "שאלות ותשובות",
        "category_en": "Q&A",
        "date": date_str,
        "year": year,
        "file": f"qa.html?id={qid}&src={src_relpath}",
        "type": "html",
        # extra fields (frontend ignores them)
        "source": meta.get("source", "Mi Yodeya"),
        "source_url": meta.get("url"),
        "tags": meta.get("tags", []),
        "source_id": qid,
        "src": src_relpath,
    }

def main():
    # Load existing responsa entries (list)
    responsa = load_json(RESPONSA_PATH, [])
    if not isinstance(responsa, list):
        raise SystemExit("responsa.json must be a JSON array")

    # Build set for dedupe: (src + id)
    existing_keys = set()
    for r in responsa:
        k = (str(r.get("src", "")), str(r.get("source_id", "")))
        if k != ("", ""):
            existing_keys.add(k)

    # Load existing QA DB for merging
    existing_db = load_json(QA_DB_PATH, {"questions": []})
    existing_questions = existing_db.get("questions", []) if isinstance(existing_db, dict) else []
    # Map of id to existing item for quick lookup
    existing_map = {str(q.get("id")): q for q in existing_questions if isinstance(q, dict)}

    merged_items = []
    new_entries = []

    # Process each MiYodea file
    for path in sorted(glob.glob(MIYODEA_GLOB)):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")  # e.g. miyodea/qa/file.json
        data = load_json(path, None)
        if not isinstance(data, list):
            # if someone uploads single-object json, normalize to list
            if isinstance(data, dict):
                data = [data]
            else:
                continue
        for item in data:
            if not isinstance(item, dict):
                continue
            qid = str(item.get("id", "")).strip()
            if not qid:
                continue
            # Flatten meta.url to top-level url if not already present
            meta = item.get("metadata") or {}
            if meta.get("url") and not item.get("url"):
                item["url"] = meta["url"]
            # Merge into existing_map (new items overwrite old ones)
            existing_map[str(qid)] = item
            merged_items.append(item)
            key = (rel, qid)
            if key not in existing_keys:
                # New responsa entry
                entry = to_responsa_entry(item, rel)
                new_entries.append(entry)
                existing_keys.add(key)

    # If we added any new MiYodea items, append to responsa
    if new_entries:
        responsa.extend(new_entries)

    # Write updated qa_db.json combining existing Yeshiva questions and new MiYodea ones
    combined_questions = list(existing_map.values())
    save_json(QA_DB_PATH, {"questions": combined_questions})
    # Save updated responsa.json
    save_json(RESPONSA_PATH, responsa)

if __name__ == "__main__":
    main()
