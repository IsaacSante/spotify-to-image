import os
import subprocess
import re
import json
import argparse
import sys

def get_ffmpeg_info(file_path):
    """
    Runs ffmpeg -i on the file and parses the output.
    Returns a dictionary with video properties or None if an error occurs.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None

    try:
        # Run ffmpeg -i, capturing stderr (where info is printed)
        process = subprocess.run(
            ['ffmpeg', '-i', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, # Get text output directly
            check=False # Don't raise exception on non-zero exit code (ffmpeg uses it for info)
        )

        # ffmpeg prints info to stderr, even on success (exit code 0 or 1 often)
        output = process.stderr

        if "Invalid data found when processing input" in output or not output:
             if process.stdout: # Check stdout too just in case
                 output += "\n" + process.stdout
             if "Invalid data found" in output or not output.strip():
                print(f"Warning: Could not process file (invalid data?): {os.path.basename(file_path)}")
                return {"file": os.path.basename(file_path), "error": "Invalid data or empty output"}


        info = {"file": os.path.basename(file_path)}

        # --- Parse General Info ---
        duration_match = re.search(r"Duration: (\d{2}:\d{2}:\d{2}\.\d{2})", output)
        if duration_match:
            info["duration"] = duration_match.group(1)

        bitrate_match = re.search(r"bitrate: (\d+\s?kb/s)", output)
        if bitrate_match:
            info["overall_bitrate"] = bitrate_match.group(1)

        # --- Parse Video Stream ---
        video_stream_match = re.search(
            r"Stream #\d+:\d+(?:\[\w+\])?\(?\w*\)?: Video: (\w+).*?,\s*(\w+).*?,\s*(\d+x\d+)(?: \[SAR.*?DAR.*?\].*?)?.*?,\s*([\d.]+)\s*kb/s.*?,\s*([\d.]+)\s*fps",
            output, re.IGNORECASE
        )
        # Simpler fallback if first fails (might miss bitrate/fps sometimes)
        if not video_stream_match:
             video_stream_match = re.search(
                r"Stream #\d+:\d+(?:\[\w+\])?\(?\w*\)?: Video: (\w+).*?,\s*(\w+).*?,\s*(\d+x\d+)",
                output, re.IGNORECASE
            )

        if video_stream_match:
            info["video_codec"] = video_stream_match.group(1)
            info["pixel_format"] = video_stream_match.group(2)
            info["resolution"] = video_stream_match.group(3)
            # Check if bitrate/fps groups exist in the match
            if len(video_stream_match.groups()) > 3:
                 info["video_bitrate"] = f"{video_stream_match.group(4)} kb/s" if video_stream_match.group(4) else "N/A"
                 info["fps"] = video_stream_match.group(5) if video_stream_match.group(5) else "N/A"
            else:
                 info["video_bitrate"] = "N/A"
                 info["fps"] = "N/A"
             # Try finding bitrate/fps separately if missed
            if info["video_bitrate"] == "N/A":
                v_bitrate_match = re.search(r"Stream #\d+:\d+.*Video:.* (\d+) kb/s", output)
                if v_bitrate_match: info["video_bitrate"] = f"{v_bitrate_match.group(1)} kb/s"
            if info["fps"] == "N/A":
                 v_fps_match = re.search(r"Stream #\d+:\d+.*Video:.* ([\d.]+) fps", output)
                 if v_fps_match: info["fps"] = v_fps_match.group(1)


        # --- Parse Audio Stream ---
        audio_stream_match = re.search(
            r"Stream #\d+:\d+(?:\[\w+\])?\(?\w*\)?: Audio: (\w+).*?,\s*(\d+)\s*Hz,\s*(\w+).*?,\s*.*?,\s*(\d+)\s*kb/s",
            output, re.IGNORECASE
        )
         # Simpler fallback if first fails
        if not audio_stream_match:
             audio_stream_match = re.search(
                r"Stream #\d+:\d+(?:\[\w+\])?\(?\w*\)?: Audio: (\w+).*?,\s*(\d+)\s*Hz,\s*(\w+)",
                output, re.IGNORECASE
            )

        if audio_stream_match:
            info["audio_codec"] = audio_stream_match.group(1)
            info["sample_rate"] = f"{audio_stream_match.group(2)} Hz"
            info["channels"] = audio_stream_match.group(3)
             # Check if bitrate group exists
            if len(audio_stream_match.groups()) > 3:
                info["audio_bitrate"] = f"{audio_stream_match.group(4)} kb/s" if audio_stream_match.group(4) else "N/A"
            else:
                info["audio_bitrate"] = "N/A"
            # Try finding bitrate separately if missed
            if info["audio_bitrate"] == "N/A":
                a_bitrate_match = re.search(r"Stream #\d+:\d+.*Audio:.* (\d+) kb/s", output)
                if a_bitrate_match: info["audio_bitrate"] = f"{a_bitrate_match.group(1)} kb/s"
        else:
            info["audio_info"] = "No audio stream detected or parsed"


        return info

    except FileNotFoundError:
        print("Error: 'ffmpeg' command not found. Make sure ffmpeg is installed and in your PATH.")
        sys.exit(1) # Exit script if ffmpeg is missing
    except Exception as e:
        print(f"An unexpected error occurred while processing {os.path.basename(file_path)}: {e}")
        return {"file": os.path.basename(file_path), "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Analyze MP4 files in a directory using ffmpeg.")
    parser.add_argument("folder_path", help="Path to the folder containing MP4 files.")
    args = parser.parse_args()

    folder_path = args.folder_path

    if not os.path.isdir(folder_path):
        print(f"Error: Folder not found: {folder_path}")
        sys.exit(1)

    all_files_info = []
    print(f"Analyzing MP4 files in: {folder_path}")
    print("-" * 30)

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".mp4"):
            file_path = os.path.join(folder_path, filename)
            print(f"Processing: {filename}...")
            info = get_ffmpeg_info(file_path)
            if info:
                all_files_info.append(info)
            print("-" * 10) # Separator after each file processing attempt


    print("\n" + "=" * 30)
    print("Analysis Complete. Results:")
    print("=" * 30 + "\n")

    # Pretty print the results
    print(json.dumps(all_files_info, indent=4))

    # Optional: Save results to a JSON file
    # output_file = os.path.join(folder_path, "video_analysis_results.json")
    # with open(output_file, 'w') as f:
    #     json.dump(all_files_info, f, indent=4)
    # print(f"\nResults also saved to: {output_file}")


if __name__ == "__main__":
    main()