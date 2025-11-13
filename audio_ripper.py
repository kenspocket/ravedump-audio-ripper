#!/usr/bin/env python3
"""
Audio Ripper Script
Extracts audio from video files (including broken/corrupted files)
Reads from: ./To_Rip/
Saves to: ./Rips/
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List

# Directories
SCRIPT_DIR = Path(__file__).parent.absolute()
SOURCE_DIR = SCRIPT_DIR / "To_Rip"
DEST_DIR = SCRIPT_DIR / "Rips"

# Supported video extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}


def create_directories():
    """Create source and destination directories if they don't exist"""
    SOURCE_DIR.mkdir(exist_ok=True)
    DEST_DIR.mkdir(exist_ok=True)
    print(f"✓ Directories ready:")
    print(f"  Source: {SOURCE_DIR}")
    print(f"  Destination: {DEST_DIR}")


def check_ffmpeg():
    """Check if ffmpeg is installed"""
    try:
        subprocess.run(['ffmpeg', '-version'],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_video_files() -> List[Path]:
    """Get all video files from the source directory"""
    video_files = []
    for file_path in SOURCE_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(file_path)
    return sorted(video_files)


def extract_audio(input_file: Path) -> bool:
    """
    Extract audio from video file using ffmpeg
    Handles broken/corrupted files with error recovery options
    """
    # Output file: same name but with .aac extension
    output_file = DEST_DIR / f"{input_file.stem}.aac"

    print(f"\nProcessing: {input_file.name}")

    # FFmpeg command with error recovery options for broken files
    # -err_detect ignore_err: Ignore errors
    # -fflags +genpts: Generate presentation timestamps
    # -vn: No video
    # -acodec copy: Copy audio codec without re-encoding (faster)
    # If copy fails, fallback to re-encoding with -acodec aac

    # Try copying audio codec first (faster)
    cmd = [
        'ffmpeg',
        '-err_detect', 'ignore_err',  # Ignore errors in broken files
        '-fflags', '+genpts',          # Generate timestamps for broken files
        '-i', str(input_file),
        '-vn',                         # No video
        '-acodec', 'copy',             # Copy audio without re-encoding
        '-y',                          # Overwrite output file
        str(output_file)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300  # 5 minute timeout per file
        )

        if result.returncode == 0:
            print(f"✓ Success: {output_file.name}")
            return True
        else:
            # If copying failed, try re-encoding
            print(f"  Codec copy failed, trying re-encoding...")
            return extract_audio_reencode(input_file, output_file)

    except subprocess.TimeoutExpired:
        print(f"✗ Timeout: {input_file.name}")
        return False
    except Exception as e:
        print(f"✗ Error: {input_file.name} - {str(e)}")
        return False


def extract_audio_reencode(input_file: Path, output_file: Path) -> bool:
    """
    Extract and re-encode audio (fallback method)
    """
    cmd = [
        'ffmpeg',
        '-err_detect', 'ignore_err',
        '-fflags', '+genpts',
        '-i', str(input_file),
        '-vn',
        '-acodec', 'aac',              # Re-encode to AAC
        '-b:a', '192k',                # Audio bitrate
        '-ar', '44100',                # Sample rate
        '-y',
        str(output_file)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print(f"✓ Success (re-encoded): {output_file.name}")
            return True
        else:
            print(f"✗ Failed: {input_file.name}")
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ Timeout: {input_file.name}")
        return False
    except Exception as e:
        print(f"✗ Error: {input_file.name} - {str(e)}")
        return False


def main():
    """Main function"""
    print("=" * 60)
    print("Audio Ripper - Extract audio from video files")
    print("=" * 60)

    # Check for ffmpeg
    if not check_ffmpeg():
        print("\n✗ ERROR: ffmpeg is not installed!")
        print("Please install ffmpeg:")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  MacOS: brew install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        sys.exit(1)

    print("✓ ffmpeg found")

    # Create directories
    create_directories()

    # Get video files
    video_files = get_video_files()

    if not video_files:
        print(f"\nNo video files found in {SOURCE_DIR}")
        print(f"Supported formats: {', '.join(sorted(VIDEO_EXTENSIONS))}")
        print("\nPlace video files in the To_Rip folder and run again.")
        return

    print(f"\nFound {len(video_files)} video file(s)")

    # Process each file
    success_count = 0
    for video_file in video_files:
        if extract_audio(video_file):
            success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Complete: {success_count}/{len(video_files)} files processed successfully")
    print(f"Audio files saved to: {DEST_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
