#!/usr/bin/env python3
"""
Utility script to automatically update the ``responsa.json`` file based on
the HTML and PDF documents located under the ``responsa`` directory.  When
new files are added to a year subdirectory (e.g. ``responsa/2025``), this
script scans the folder structure, extracts minimal metadata from each
document and appends entries for unknown files to the JSON archive.  It
avoids duplicating existing entries by checking the ``file`` field.

Key points:

* Supported document types are HTML/HTM and PDF.  Unknown file types are
  ignored.
* Titles are taken from the FIRST <h1> element (not <title>), or from
  filename if no <h1> is found. This avoids duplicate generic titles.
* Summaries are generated from the first roughly 50 words of the document's
  text when possible.  If BeautifulSoup (from the ``bs4`` package) is
  unavailable or parsing fails, both title and summary default to the
  filename and an empty string respectively.
* Categories default to ``other`` with multilingual labels (``אחר`` and
  ``Other``).  You can adjust this logic as needed.
* Dates are based on the file's last modification time on disk and are
  formatted as ``dd/mm/YYYY``.  The year field is extracted from this date.
* Entry numbers are assigned sequentially starting from the largest number
  present in the existing JSON.  New entries increment this counter.

Usage:

    python3 update_responsa.py

Run this script from the project root (the directory containing
``responsa.json``).  It will update ``responsa.json`` in place and report
how many new entries were added.  If the ``responsa`` directory does not
exist, the script exits silently.
"""

import os
import json
import datetime
import sys
from pathlib import Path

# Attempt to import BeautifulSoup for robust HTML parsing.  If unavailable,
# fall back to simple string-based parsing.
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None  # type: ignore


def extract_metadata_from_html(path: Path) -> tuple[str, str]:
    """Extract a (title, summary) tuple from an HTML file.

    Priority for title extraction:
    1. First <h1> tag (the actual document title)
    2. Filename without extension (fallback)
    
    We AVOID using <title> tag because it's often the generic website title
    (e.g. "בית דין גדול סנהדרין") which is the same on all pages.
    
    If BeautifulSoup is available it will parse the document and extract
    the first ~50 words of visible text for the summary.
    """
    title = path.stem  # Default: filename without extension
    summary = ""
    
    if BeautifulSoup is None:
        # Without BeautifulSoup we cannot reliably parse HTML.  Use the
        # filename as the title and leave the summary empty.
        return title, summary
    
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        
        # Title extraction: Use FIRST <h1> tag (actual document title)
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.get_text(strip=True):
            title = h1_tag.get_text(strip=True)
        else:
            # Fallback: use filename if no <h1> found
            title = path.stem
        
        # Summary extraction: remove scripts/styles and collect first words
        for tag in soup(["script", "style", "meta", "link"]):
            tag.decompose()
        
        text = soup.get_text(separator=" ", strip=True)
        words = text.split()
        
        if words:
            summary = " ".join(words[:50])
            if len(words) > 50:
                summary += "..."
    
    except Exception as e:
        # In case of any parsing error, fall back to filename
        print(f"Warning: Could not parse {path.name}: {e}")
        title = path.stem
        summary = ""
    
    return title, summary


def extract_metadata(path: Path) -> dict:
    """Build a metadata dictionary for a given document file.

    For HTML files additional parsing is attempted.  For PDFs and other
    supported types the title falls back to the filename and summaries are
    left blank.  The date and year are derived from the file's
    modification time.
    """
    ext = path.suffix.lower()
    file_type = "html" if ext in {".html", ".htm"} else "pdf"
    
    # Use modification time for date
    mtime = path.stat().st_mtime
    dt = datetime.datetime.fromtimestamp(mtime)
    date_str = dt.strftime("%d/%m/%Y")
    year = dt.year
    
    # Parse title and summary
    if file_type == "html":
        title, summary = extract_metadata_from_html(path)
    else:
        # For PDFs, use filename
        title = path.stem
        summary = ""
    
    # Assemble entry with placeholders for category labels
    entry = {
        "title_he": title,
        "title_en": title,
        "summary_he": summary,
        "summary_en": summary,
        "category": "other",
        "category_he": "אחר",
        "category_en": "Other",
        "date": date_str,
        "year": year,
        "file": str(path.as_posix()),
        "type": file_type,
    }
    return entry


def main() -> int:
    # Determine project root based on this script's location
    root = Path(__file__).resolve().parent
    responsa_dir = root / "responsa"
    json_path = root / "responsa.json"
    
    # Bail out silently if there is no responsa directory
    if not responsa_dir.is_dir():
        print("No 'responsa' directory found. Nothing to update.")
        return 0
    
    # Load existing JSON data
    existing_data: list[dict] = []
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            # If JSON is malformed, start with an empty list
            existing_data = []
    
    # Build a mapping of known files to their entries for quick lookup
    existing_map = {entry.get("file"): entry for entry in existing_data if isinstance(entry, dict)}
    
    # Determine the next available number
    existing_numbers = [entry.get("number", 0) for entry in existing_data if isinstance(entry.get("number"), int)]
    next_number = max(existing_numbers, default=0) + 1
    
    new_entries: list[dict] = []
    
    # Walk through the responsa directory
    for file_path in responsa_dir.rglob("*"):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in {".html", ".htm", ".pdf"}:
            continue
        rel_path = file_path.relative_to(root).as_posix()
        if rel_path in existing_map:
            continue  # skip files already present in the JSON
        
        # Extract metadata and assign a new number
        metadata = extract_metadata(file_path)
        # Override the file field with a POSIX-style relative path.  Using
        # relative paths ensures that the resulting JSON does not contain
        # absolute paths specific to the local filesystem.
        metadata["file"] = rel_path
        metadata["number"] = next_number
        next_number += 1
        
        new_entries.append(metadata)
        
        # Show what was found
        print(f"  Found: {metadata['title_he'][:60]}..." if len(metadata['title_he']) > 60 else f"  Found: {metadata['title_he']}")
    
    # If no new entries were found, report and exit
    if not new_entries:
        print("No new responsa found. 'responsa.json' is up to date.")
        return 0
    
    # Append and sort combined data by number
    updated_data = existing_data + new_entries
    updated_data.sort(key=lambda x: x.get("number", 0))
    
    # Write back to JSON file
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)
    
    print(f"Added {len(new_entries)} new entr{'y' if len(new_entries) == 1 else 'ies'} to 'responsa.json'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
