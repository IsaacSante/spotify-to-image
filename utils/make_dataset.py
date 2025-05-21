#!/usr/bin/env python3
"""
extract_frames.py

Scan all .mp4 files in `VIDEO_DIR`, pull a frame every 3 s (stopping when
<10 s remain), and save them as JPGs to `OUT_DIR` with names like:
    001-00:03.jpg, 001-00:06.jpg, …
"""

import os
from pathlib import Path
import cv2  # pip install opencv-python-headless (or opencv-python)

# --- configuration ----------------------------------------------------------
VIDEO_DIR = Path("/Users/isaacsante/Documents/GitHub/text-to-img/video_dataset/videos")
OUT_DIR   = Path("/Users/isaacsante/Documents/GitHub/text-to-img/video_dataset/images")
STEP_SEC  = 3                 # sample every 3 seconds
TAIL_SKIP = 10                # skip final ≤10 s of each video
# ---------------------------------------------------------------------------

def timestamp_str(seconds: float) -> str:
    """Return MM:SS string with zero-padding (e.g. 3 -> '00:03')."""
    minutes = int(seconds // 60)
    secs    = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def extract_frames(video_path: Path) -> None:
    vid_id = video_path.stem                 # '001' from '001.mp4'
    cap    = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"[WARN] Cannot open {video_path}")
        return

    fps       = cap.get(cv2.CAP_PROP_FPS) or 30  # fallback if FPS unavailable
    n_frames  = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration  = n_frames / fps if fps else 0

    if duration <= TAIL_SKIP:                 # video too short – skip entirely
        print(f"[INFO] {video_path.name}: length {duration:.1f}s < {TAIL_SKIP}s, skipping.")
        cap.release()
        return

    t = STEP_SEC
    while t <= duration - TAIL_SKIP:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)  # seek to t seconds
        ret, frame = cap.read()
        if not ret:
            print(f"[WARN] Failed at {video_path.name} @ {t}s")
            break

        ts   = timestamp_str(t)
        out  = OUT_DIR / f"{vid_id}-{ts}.jpg"
        cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"  • saved {out.name}")
        t += STEP_SEC

    cap.release()

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mp4_files = sorted(p for p in VIDEO_DIR.glob("*.mp4"))
    if not mp4_files:
        print(f"No videos found in {VIDEO_DIR}")
        return

    for video in mp4_files:
        print(f"[PROCESS] {video.name}")
        extract_frames(video)

if __name__ == "__main__":
    main()
