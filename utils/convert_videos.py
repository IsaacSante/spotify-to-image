#!/usr/bin/env python3
"""
convert_to_mp4.py
Convert every video in the target directory (recursively) to H.264 MP4.

Usage:
    python convert_to_mp4.py /path/to/playlist_downloads
"""
import subprocess
import sys
from pathlib import Path
import shlex

# ---------- CONFIG ----------
CRF = 23           # quality (lower = better; 18-23 is typical)
PRESET = "veryfast"  # encoding speed / compression trade-off
AUDIO_BR = "192k"    # audio bitrate
# ----------------------------

def has_h264_video(streams_line: str) -> bool:
    """Quick-and-dirty check for H.264 in ffprobe stream info."""
    return "Video: h264" in streams_line or "Video: libx264" in streams_line

def main():
    if len(sys.argv) != 2:
        sys.exit("Pass the directory to process, e.g. python convert_to_mp4.py playlist_downloads")

    target_dir = Path(sys.argv[1]).expanduser().resolve()
    if not target_dir.is_dir():
        sys.exit(f"{target_dir} is not a directory")

    videos = [p for p in target_dir.rglob("*") if p.is_file()]
    if not videos:
        sys.exit("No files found")

    for vid in videos:
        # Skip hidden/system files
        if vid.name.startswith("."):
            continue

        # Check if already an H.264 MP4
        if vid.suffix.lower() == ".mp4":
            try:
                # probe the first video stream only
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_streams", "-of", "compact=p=0:nk=1", vid],
                    stdout=subprocess.PIPE, text=True, check=True
                )
                if has_h264_video(result.stdout):
                    print(f"✅  Skipping (already H.264): {vid.name}")
                    continue
            except subprocess.CalledProcessError as e:
                print(f"⚠️  ffprobe failed on {vid.name}: {e}. Will re-encode.")

        # Build output path
        out_path = vid.with_suffix(".mp4")
        if out_path.exists():
            out_path = out_path.with_stem(out_path.stem + "_converted")

        cmd = [
            "ffmpeg", "-y", "-i", str(vid),
            "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
            "-c:a", "aac", "-b:a", AUDIO_BR,
            "-movflags", "+faststart",
            str(out_path)
        ]

        print(f"→ Converting {vid.name} → {out_path.name}")
        try:
            subprocess.run(cmd, check=True)
            print(f"   ✅  Created {out_path.name}")
        except subprocess.CalledProcessError:
            print(f"   ❌  ffmpeg failed for {vid.name}")

if __name__ == "__main__":
    main()
