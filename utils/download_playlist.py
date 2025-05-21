#!/usr/bin/env python3
"""
download_playlist_simple.py
===========================

Download every public video in a YouTube playlist exactly as-is.

•  Uses yt-dlp’s “lazy” pagination so the notorious
   “Incomplete data received” bug can’t kill the run.
•  Skips any item that errors instead of aborting.
•  Shows a basic progress bar (requires no extra library).

That’s it—no re-encoding, no cookies, no command-line args.
"""

import sys, itertools, math
from pathlib import Path
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# --- edit these two lines if you like ---------------------------------
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLkn3D5c4Estrw5J5hkTdNwbxqnD25xXnc"
OUT_DIR      = Path.cwd() / "playlist_downloads"
# ----------------------------------------------------------------------

def human_bar(done, total, width=30):
    filled = math.floor(width * done / total)
    return "[" + "█"*filled + "░"*(width - filled) + f"] {done}/{total}"

def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    ydl_opts = {
        "outtmpl": str(OUT_DIR / "%(playlist_index)05d_%(title).200s.%(ext)s"),
        "format":  "bestvideo+bestaudio/best",   # grab best combined stream available
        "quiet":   True,
        "ignoreerrors": True,
        "lazy_playlist": True,      # walk page-by-page (fixes JSON truncation issue)
        "retries": 5,
        "fragment_retries": 5,
    }

    # First pass: count how many entries we *should* get, for a progress bar
    with YoutubeDL({**ydl_opts, "extract_flat": "in_playlist"}) as ydl:
        pl_info   = ydl.extract_info(PLAYLIST_URL, download=False)
        entries   = [e for e in pl_info["entries"] if e]
        total     = len(entries)

    print(f"Found {total} videos. Starting download …")

    # Tiny in-place progress bar (no external deps)
    finished = 0
    def hook(d):
        nonlocal finished
        if d["status"] == "finished":
            finished += 1
            bar = human_bar(finished, total)
            print("\r" + bar, end="", flush=True)

    ydl_opts["progress_hooks"] = [hook]

    failures = []
    with YoutubeDL(ydl_opts) as ydl:
        for entry in entries:
            try:
                ydl.download([entry["url"]])
            except DownloadError:
                failures.append(entry.get("title", "unknown title"))

    print()  # newline after bar
    if failures:
        print("\nCompleted with warnings — these videos were skipped:")
        for t in failures:
            print("  •", t)
    else:
        print("\nAll videos downloaded successfully.")

if __name__ == "__main__":
    if sys.version_info < (3, 8):
        sys.exit("Python 3.8+ required.")
    main()
