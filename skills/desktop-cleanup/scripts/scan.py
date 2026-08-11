#!/usr/bin/env python3
"""Deterministic bookkeeping for the desktop-cleanup skill.

Subcommands:
  config                      Print the current config.json (or {} if unset)
  init-config                 Write config.json from --media/--books/--personal-docs
  scan                        Walk the four roots, update history.json, print stale candidates
  sample-dest --path P        List entries under a destination folder (metadata only)
  compare --a A --b B         Compare two paths by size only (never reads content)
  record --path P --decision  Record a decision (declined/moved/trashed) for a path

All state lives under ~/.desktop-cleanup/ (config.json, history.json), separate
from the plugin's own repo since it's per-machine, per-user data.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

STATE_DIR = os.path.expanduser("~/.desktop-cleanup")
CONFIG_PATH = os.path.join(STATE_DIR, "config.json")
HISTORY_PATH = os.path.join(STATE_DIR, "history.json")

ROOTS = {
    "Downloads": os.path.expanduser("~/Downloads"),
    "Developer": os.path.expanduser("~/Developer"),
    "Documents": os.path.expanduser("~/Documents"),
    "Desktop": os.path.expanduser("~/Desktop"),
}

STALE_DAYS = {
    "Downloads": 30,
    "Developer": 180,
    "Documents": 180,
    "Desktop": 180,
}

SKIP_DIR_NAMES = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
MIN_SCAN_COUNT = 2


def today_str():
    return datetime.now(timezone.utc).date().isoformat()


def load_json(path):
    if not os.path.isfile(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def is_repo_dir(dirpath):
    return os.path.exists(os.path.join(dirpath, ".git"))


def should_skip_dir(name):
    return name in SKIP_DIR_NAMES or name.startswith(".") or name.endswith(".app")


def cmd_config(args):
    print(json.dumps(load_json(CONFIG_PATH), indent=2))


def cmd_init_config(args):
    cfg = {
        "media": args.media,
        "books": args.books,
        "personal_docs": args.personal_docs,
    }
    save_json(CONFIG_PATH, cfg)
    print(json.dumps(cfg, indent=2))


def walk_root(root_name, root_path):
    """Yield (filepath, mtime_epoch, size) for every non-skipped file under root_path."""
    if not os.path.isdir(root_path):
        return
    for dirpath, dirnames, filenames in os.walk(root_path):
        base = os.path.basename(dirpath)
        if dirpath != root_path and is_repo_dir(dirpath):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for name in filenames:
            if name.startswith("."):
                continue
            fpath = os.path.join(dirpath, name)
            try:
                st = os.lstat(fpath)
            except OSError:
                continue
            yield fpath, st.st_mtime, st.st_size


def cmd_scan(args):
    history = load_json(HISTORY_PATH)
    files = history.setdefault("files", {})
    today = today_str()
    candidates = []
    seen_paths = set()

    for root_name, root_path in ROOTS.items():
        for fpath, mtime_epoch, size in walk_root(root_name, root_path):
            seen_paths.add(fpath)
            mtime_date = datetime.fromtimestamp(mtime_epoch, tz=timezone.utc).date().isoformat()
            age_days = (datetime.now(timezone.utc).date() - datetime.fromtimestamp(mtime_epoch, tz=timezone.utc).date()).days

            entry = files.get(fpath)
            if entry is None:
                entry = {
                    "first_seen": today,
                    "last_seen": today,
                    "mtime": mtime_date,
                    "scan_count": 1,
                    "decision": None,
                }
                files[fpath] = entry
            else:
                if entry.get("mtime") != mtime_date:
                    # File changed since we last saw it — restart the staleness clock.
                    entry["mtime"] = mtime_date
                    entry["scan_count"] = 1
                    entry["decision"] = None
                    entry["first_seen"] = today
                else:
                    entry["scan_count"] = entry.get("scan_count", 0) + 1
                entry["last_seen"] = today

            threshold = STALE_DAYS[root_name]
            is_stale = age_days >= threshold and entry["scan_count"] >= MIN_SCAN_COUNT
            if is_stale and entry.get("decision") != "declined":
                candidates.append({
                    "path": fpath,
                    "root": root_name,
                    "size": size,
                    "mtime": mtime_date,
                    "age_days": age_days,
                    "first_seen": entry["first_seen"],
                    "scan_count": entry["scan_count"],
                })

    # Drop history entries for files that no longer exist (moved/trashed/renamed elsewhere).
    for stale_path in [p for p in files if p not in seen_paths]:
        del files[stale_path]

    save_json(HISTORY_PATH, history)
    print(json.dumps({"candidates": candidates, "scanned_at": today}, indent=2))


def cmd_sample_dest(args):
    target = os.path.expanduser(args.path)
    if not os.path.isdir(target):
        print(json.dumps({"error": f"not a directory: {target}"}))
        return
    entries = []
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), target)
            entries.append(rel)
            if len(entries) >= args.limit:
                break
        if len(entries) >= args.limit:
            break
    print(json.dumps({"root": target, "entries": entries}, indent=2))


def cmd_compare(args):
    def stat_or_none(p):
        try:
            return os.stat(os.path.expanduser(p)).st_size
        except OSError:
            return None

    size_a = stat_or_none(args.a)
    size_b = stat_or_none(args.b)
    match = None
    if size_a is not None and size_b is not None:
        match = size_a == size_b
    print(json.dumps({"a_size": size_a, "b_size": size_b, "match": match}, indent=2))


def cmd_record(args):
    history = load_json(HISTORY_PATH)
    files = history.setdefault("files", {})
    fpath = os.path.expanduser(args.path)
    entry = files.get(fpath, {})
    entry["decision"] = args.decision
    entry["decided_at"] = today_str()
    files[fpath] = entry
    save_json(HISTORY_PATH, history)
    print(json.dumps(entry, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("config").set_defaults(func=cmd_config)

    p = sub.add_parser("init-config")
    p.add_argument("--media", required=True)
    p.add_argument("--books", required=True)
    p.add_argument("--personal-docs", required=True, dest="personal_docs")
    p.set_defaults(func=cmd_init_config)

    sub.add_parser("scan").set_defaults(func=cmd_scan)

    p = sub.add_parser("sample-dest")
    p.add_argument("--path", required=True)
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(func=cmd_sample_dest)

    p = sub.add_parser("compare")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("record")
    p.add_argument("--path", required=True)
    p.add_argument("--decision", required=True, choices=["declined", "moved", "trashed"])
    p.set_defaults(func=cmd_record)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
