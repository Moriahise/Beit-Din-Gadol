#!/usr/bin/env python3
import json
import glob
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))  # repo root
RESPONSA_PATH = os.path.join(ROOT, "responsa.json")
QA_DB_PATH = os.path.join(ROOT, "qa_db.json")
MIYODEA_GLOB = os.path.join(ROOT, "miyodea", "qa", "*.json")

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_summary_from_content(content: str) -> str:
    # Take first ~220 chars of plain-ish text
    s = (content or "").replace("\n", " ").strip()
    return (s[:220] + "…") if len(s) > 220 else s

def extract_year(meta_date: str) -> int:
    # meta_date like "2010-12-21T16:53:44"
    if not meta_date:
        return datetime.utcnow().year
    try:
        return int(meta_date[:4])
    except Exception:
        return datetime.utcnow().year

def to_responsa_entry(item, src_relpath: str):
    meta = item.get("metadata", {}) or {}
    qid = str(item.get("id", "")).strip()

    # number: try to use digits from id, else fallback hash-ish
    digits = "".join(ch for ch in qid if ch.isdigit())
    number = int(digits) if digits else 0

    year = extract_year(meta.get("date"))
    date_str = ""
    if meta.get("date"):
        date_str = meta["date"][:10]  # YYYY-MM-DD
    else:
        date_str = f"{year}-01-01"

    title = item.get("title") or f"Q&A {qid}"
    summary = normalize_summary_from_content(item.get("content", ""))

    # IMPORTANT: keep existing categories untouched; use "other" so index filter doesn't break :contentReference[oaicite:9]{index=9}
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
        # extra fields (safe: frontend ignores them)
        "source": meta.get("source", "Mi Yodeya"),
        "source_url": meta.get("url"),
        "tags": meta.get("tags", []),
        "source_id": qid,
        "src": src_relpath,
    }

def main():
    responsa = load_json(RESPONSA_PATH, [])
    if not isinstance(responsa, list):
        raise SystemExit("responsa.json must be a JSON array")

    # Build set for dedupe: (src + id)
    existing_keys = set()
    for r in responsa:
        k = (str(r.get("src", "")), str(r.get("source_id", "")))
        if k != ("", ""):
            existing_keys.add(k)

    merged_items = []
    new_entries = []

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

            merged_items.append(item)

            key = (rel, qid)
            if key in existing_keys:
                continue

            entry = to_responsa_entry(item, rel)
            new_entries.append(entry)
            existing_keys.add(key)

    if new_entries:
        responsa.extend(new_entries)

    # Write qa_db.json as merged array (optional but handy for future)
    save_json(QA_DB_PATH, {"questions": merged_items})

    # Save responsa.json
    save_json(RESPONSA_PATH, responsa)

if __name__ == "__main__":
    main()
