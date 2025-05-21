#!/usr/bin/env python3
"""
extract_frames_from_200.py

Same as extract_frames.py, but only processes .mp4 files
with a numeric stem of 200 or higher.
"""

import os
from pathlib import Path
import cv2  # pip install opencv-python-headless (or opencv-python)

# --- configuration ----------------------------------------------------------
VIDEO_DIR = Path("/Users/isaacsante/Documents/GitHub/text-to-img/video_dataset/videos")
OUT_DIR   = Path("/Users/isaacsante/Documents/GitHub/text-to-img/video_dataset/images")
STEP_SEC  = 3                 # sample every 3 seconds
TAIL_SKIP = 10                # skip final ≤10 s of each video

START_AT  = 200               # only process files ≥ this numeric ID
# ---------------------------------------------------------------------------

def timestamp_str(seconds: float) -> str:
    """Return MM:SS string with zero-padding (e.g. 3 -> '00:03')."""
    minutes = int(seconds // 60)
    secs    = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def extract_frames(video_path: Path) -> None:
    vid_id = video_path.stem  # e.g. '200' from '200.mp4'
    cap    = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"[WARN] Cannot open {video_path}")
        return

    fps      = cap.get(cv2.CAP_PROP_FPS) or 30
    n_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = n_frames / fps if fps else 0

    if duration <= TAIL_SKIP:
        print(f"[INFO] {video_path.name}: length {duration:.1f}s < {TAIL_SKIP}s, skipping.")
        cap.release()
        return

    t = STEP_SEC
    while t <= duration - TAIL_SKIP:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if not ret:
            print(f"[WARN] Failed at {video_path.name} @ {t}s")
            break

        ts  = timestamp_str(t)
        out = OUT_DIR / f"{vid_id}-{ts}.jpg"
        cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"  • saved {out.name}")
        t += STEP_SEC

    cap.release()

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # numeric sort, then filter to only IDs >= START_AT
    mp4_files = sorted(
        VIDEO_DIR.glob("*.mp4"),
        key=lambda p: int(p.stem)
    )
    mp4_files = [p for p in mp4_files if int(p.stem) >= START_AT]

    if not mp4_files:
        print(f"No videos ≥ {START_AT} found in {VIDEO_DIR}")
        return

    for video in mp4_files:
        print(f"[PROCESS] {video.name}")
        extract_frames(video)

if __name__ == "__main__":
    main()
