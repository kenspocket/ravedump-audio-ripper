#!/usr/bin/env python3
"""
RAVEDUMP RIPPER - Audio Extraction Tool
Extracts audio from video files (including broken/corrupted files)
Reads from: ./To_Rip/
Saves to: ./Rips/
"""

import os
import subprocess
import sys
import time
import re
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm not installed. Install with: pip3 install tqdm")
    sys.exit(1)

# Directories
SCRIPT_DIR = Path(__file__).parent.absolute()
SOURCE_DIR = SCRIPT_DIR / "To_Rip"
DEST_DIR = SCRIPT_DIR / "Rips"

# Supported video extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}

# Statistics
stats = {
    'total_files': 0,
    'successful': 0,
    'failed': 0,
    'copied': 0,
    'reencoded': 0,
    'total_size_input': 0,
    'total_size_output': 0,
    'start_time': None,
    'end_time': None
}


def print_banner():
    """Print ASCII art banner"""
    banner = r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ██████╗  █████╗ ██╗   ██╗███████╗██████╗ ██╗   ██╗███╗   ███╗██████╗     ║
║   ██╔══██╗██╔══██╗██║   ██║██╔════╝██╔══██╗██║   ██║████╗ ████║██╔══██╗    ║
║   ██████╔╝███████║██║   ██║█████╗  ██║  ██║██║   ██║██╔████╔██║██████╔╝    ║
║   ██╔══██╗██╔══██║╚██╗ ██╔╝██╔══╝  ██║  ██║██║   ██║██║╚██╔╝██║██╔═══╝     ║
║   ██║  ██║██║  ██║ ╚████╔╝ ███████╗██████╔╝╚██████╔╝██║ ╚═╝ ██║██║         ║
║   ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═╝         ║
║                                                                              ║
║                ██████╗ ██╗██████╗ ██████╗ ███████╗██████╗                   ║
║                ██╔══██╗██║██╔══██╗██╔══██╗██╔════╝██╔══██╗                  ║
║                ██████╔╝██║██████╔╝██████╔╝█████╗  ██████╔╝                  ║
║                ██╔══██╗██║██╔═══╝ ██╔═══╝ ██╔══╝  ██╔══██╗                  ║
║                ██║  ██║██║██║     ██║     ███████╗██║  ██║                  ║
║                ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝     ╚══════╝╚═╝  ╚═╝                  ║
║                                                                              ║
║                    Audio Extraction & Recovery Tool v2.0                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def create_directories():
    """Create source and destination directories if they don't exist"""
    SOURCE_DIR.mkdir(exist_ok=True)
    DEST_DIR.mkdir(exist_ok=True)


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


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes"""
    try:
        return file_path.stat().st_size
    except:
        return 0


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def format_time(seconds: float) -> str:
    """Format seconds to human readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def get_video_files() -> List[Path]:
    """Get all video files from the source directory"""
    video_files = []
    for file_path in SOURCE_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(file_path)
    return sorted(video_files)


def get_video_duration(file_path: Path) -> Optional[float]:
    """Get video duration in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except:
        pass
    return None


def extract_audio_with_progress(input_file: Path, progress_bar: tqdm) -> Tuple[bool, str]:
    """
    Extract audio from video file using ffmpeg with progress monitoring
    Returns: (success, method) where method is 'copy', 'reencode', or 'failed'
    """
    output_file = DEST_DIR / f"{input_file.stem}.aac"

    # Update progress bar description
    progress_bar.set_description(f"[RIPPING] {input_file.name[:40]}")

    # Get video duration for progress calculation
    duration = get_video_duration(input_file)

    # Try copying audio codec first (faster)
    cmd = [
        'ffmpeg',
        '-err_detect', 'ignore_err',
        '-fflags', '+genpts',
        '-i', str(input_file),
        '-vn',
        '-acodec', 'copy',
        '-progress', 'pipe:1',
        '-y',
        str(output_file)
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Monitor progress
        for line in process.stdout:
            if duration and 'out_time_ms=' in line:
                try:
                    time_ms = int(line.split('=')[1])
                    time_s = time_ms / 1000000
                    percent = min(100, (time_s / duration) * 100)
                    progress_bar.set_postfix(progress=f"{percent:.1f}%", method="COPY")
                except:
                    pass

        process.wait(timeout=300)

        if process.returncode == 0 and output_file.exists():
            progress_bar.set_postfix(status="✓ COPIED", size=format_size(get_file_size(output_file)))
            stats['copied'] += 1
            return True, 'copy'
        else:
            # Try re-encoding
            progress_bar.set_description(f"[RE-ENC] {input_file.name[:40]}")
            return extract_audio_reencode(input_file, output_file, progress_bar)

    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        progress_bar.set_postfix(status="✗ TIMEOUT")
        return False, 'failed'
    except Exception as e:
        progress_bar.set_postfix(status=f"✗ ERROR")
        return False, 'failed'


def extract_audio_reencode(input_file: Path, output_file: Path, progress_bar: tqdm) -> Tuple[bool, str]:
    """
    Extract and re-encode audio (fallback method)
    """
    duration = get_video_duration(input_file)

    cmd = [
        'ffmpeg',
        '-err_detect', 'ignore_err',
        '-fflags', '+genpts',
        '-i', str(input_file),
        '-vn',
        '-acodec', 'aac',
        '-b:a', '192k',
        '-ar', '44100',
        '-progress', 'pipe:1',
        '-y',
        str(output_file)
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            if duration and 'out_time_ms=' in line:
                try:
                    time_ms = int(line.split('=')[1])
                    time_s = time_ms / 1000000
                    percent = min(100, (time_s / duration) * 100)
                    progress_bar.set_postfix(progress=f"{percent:.1f}%", method="RE-ENC")
                except:
                    pass

        process.wait(timeout=300)

        if process.returncode == 0 and output_file.exists():
            progress_bar.set_postfix(status="✓ RE-ENC", size=format_size(get_file_size(output_file)))
            stats['reencoded'] += 1
            return True, 'reencode'
        else:
            progress_bar.set_postfix(status="✗ FAILED")
            return False, 'failed'

    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        progress_bar.set_postfix(status="✗ TIMEOUT")
        return False, 'failed'
    except Exception as e:
        progress_bar.set_postfix(status="✗ ERROR")
        return False, 'failed'


def process_files(video_files: List[Path]):
    """Process all video files with progress bars"""
    stats['start_time'] = time.time()
    stats['total_files'] = len(video_files)

    print("\n" + "═" * 80)
    print("STARTING RIP PROCESS")
    print("═" * 80 + "\n")

    # Main progress bar for overall progress
    with tqdm(total=len(video_files),
              desc="[OVERALL]",
              unit="file",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
              position=0) as pbar:

        for video_file in video_files:
            # Calculate input size
            input_size = get_file_size(video_file)
            stats['total_size_input'] += input_size

            # Process file
            success, method = extract_audio_with_progress(video_file, pbar)

            if success:
                stats['successful'] += 1
                output_file = DEST_DIR / f"{video_file.stem}.aac"
                stats['total_size_output'] += get_file_size(output_file)
            else:
                stats['failed'] += 1

            pbar.update(1)
            time.sleep(0.1)  # Small delay for visual clarity

    stats['end_time'] = time.time()


def print_statistics():
    """Print detailed statistics"""
    duration = stats['end_time'] - stats['start_time']

    print("\n" + "═" * 80)
    print("RIP COMPLETE - STATISTICS")
    print("═" * 80)
    print(f"Total Files:        {stats['total_files']}")
    print(f"  ✓ Successful:     {stats['successful']} ({stats['successful']/stats['total_files']*100:.1f}%)")
    print(f"  ✗ Failed:         {stats['failed']}")
    print(f"\nExtraction Methods:")
    print(f"  Fast Copy:        {stats['copied']}")
    print(f"  Re-encoded:       {stats['reencoded']}")
    print(f"\nData Processed:")
    print(f"  Input Size:       {format_size(stats['total_size_input'])}")
    print(f"  Output Size:      {format_size(stats['total_size_output'])}")

    if stats['total_size_input'] > 0:
        compression = (1 - stats['total_size_output'] / stats['total_size_input']) * 100
        print(f"  Compression:      {compression:.1f}%")

    print(f"\nTime Elapsed:       {format_time(duration)}")
    if duration > 0:
        avg_time = duration / stats['total_files']
        print(f"Average per file:   {format_time(avg_time)}")

    print(f"\nOutput Directory:   {DEST_DIR}")
    print("═" * 80 + "\n")


def list_files():
    """List all video files in To_Rip folder"""
    video_files = get_video_files()

    if not video_files:
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║  NO FILES FOUND                                                ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"\nNo video files in: {SOURCE_DIR}")
        print(f"Supported formats: {', '.join(sorted(VIDEO_EXTENSIONS))}")
        return

    print("\n╔════════════════════════════════════════════════════════════════╗")
    print(f"║  FILES IN TO_RIP FOLDER: {len(video_files)} file(s)")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    total_size = 0
    for i, file_path in enumerate(video_files, 1):
        size = get_file_size(file_path)
        total_size += size
        duration = get_video_duration(file_path)
        dur_str = f" [{format_time(duration)}]" if duration else ""
        print(f"  {i:2d}. {file_path.name[:50]:50s} {format_size(size):>10s}{dur_str}")

    print(f"\n  Total size: {format_size(total_size)}")


def view_output():
    """View files in Rips folder"""
    output_files = sorted([f for f in DEST_DIR.iterdir() if f.is_file()])

    if not output_files:
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║  NO OUTPUT FILES                                               ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"\nNo files in: {DEST_DIR}")
        return

    print("\n╔════════════════════════════════════════════════════════════════╗")
    print(f"║  FILES IN RIPS FOLDER: {len(output_files)} file(s)")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    total_size = 0
    for i, file_path in enumerate(output_files, 1):
        size = get_file_size(file_path)
        total_size += size
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        print(f"  {i:2d}. {file_path.name[:50]:50s} {format_size(size):>10s}  [{mod_time}]")

    print(f"\n  Total size: {format_size(total_size)}")


def show_menu():
    """Display CLI menu"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║                         MAIN MENU                              ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print("║  1. Start Ripping (Process all files)                         ║")
    print("║  2. List files in To_Rip folder                               ║")
    print("║  3. View output in Rips folder                                ║")
    print("║  4. System check (ffmpeg, directories)                        ║")
    print("║  5. Clear Rips folder                                         ║")
    print("║  6. About                                                     ║")
    print("║  0. Exit                                                      ║")
    print("╚════════════════════════════════════════════════════════════════╝")


def system_check():
    """Check system requirements"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║  SYSTEM CHECK                                                  ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    # Check ffmpeg
    if check_ffmpeg():
        print("  ✓ ffmpeg installed")
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            version_line = result.stdout.split('\n')[0]
            print(f"    {version_line}")
        except:
            pass
    else:
        print("  ✗ ffmpeg NOT installed")
        print("    Install: sudo apt-get install ffmpeg")

    # Check directories
    print(f"\n  Directories:")
    print(f"    Source:      {SOURCE_DIR} {'✓' if SOURCE_DIR.exists() else '✗'}")
    print(f"    Destination: {DEST_DIR} {'✓' if DEST_DIR.exists() else '✗'}")

    # Check Python version
    print(f"\n  Python:      {sys.version.split()[0]} ✓")

    # Check tqdm
    print(f"  tqdm:        Installed ✓")


def clear_rips_folder():
    """Clear all files in Rips folder"""
    output_files = list(DEST_DIR.glob('*'))
    output_files = [f for f in output_files if f.is_file()]

    if not output_files:
        print("\n  Rips folder is already empty.")
        return

    print(f"\n  Found {len(output_files)} file(s) in Rips folder.")
    confirm = input("  Delete all files? (yes/no): ").strip().lower()

    if confirm == 'yes':
        for file_path in output_files:
            try:
                file_path.unlink()
            except:
                print(f"  ✗ Failed to delete: {file_path.name}")
        print(f"  ✓ Deleted {len(output_files)} file(s)")
    else:
        print("  Cancelled.")


def show_about():
    """Show about information"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║  RAVEDUMP RIPPER v2.0                                          ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print("║  Advanced audio extraction tool for video files               ║")
    print("║                                                                ║")
    print("║  Features:                                                     ║")
    print("║  • Extract audio from any video format                        ║")
    print("║  • Handle broken/corrupted files                              ║")
    print("║  • Smart codec detection and copying                          ║")
    print("║  • Automatic fallback to re-encoding                          ║")
    print("║  • Real-time progress tracking                                ║")
    print("║  • Detailed statistics                                        ║")
    print("║                                                                ║")
    print("║  Supports: MP4, AVI, MKV, MOV, FLV, WMV, WebM, M4V, MPG       ║")
    print("╚════════════════════════════════════════════════════════════════╝")


def main():
    """Main function with CLI menu"""
    print_banner()

    # Create directories
    create_directories()

    # Check ffmpeg
    if not check_ffmpeg():
        print("\n✗ ERROR: ffmpeg is not installed!")
        print("Please install ffmpeg:")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  MacOS: brew install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        input("\nPress Enter to exit...")
        sys.exit(1)

    while True:
        show_menu()
        choice = input("\nSelect option: ").strip()

        if choice == '1':
            video_files = get_video_files()
            if not video_files:
                print("\n✗ No video files found in To_Rip folder!")
                print("  Add video files and try again.")
                input("\nPress Enter to continue...")
                continue

            print(f"\n  Found {len(video_files)} file(s) ready to rip.")
            confirm = input("  Start ripping? (yes/no): ").strip().lower()

            if confirm == 'yes':
                process_files(video_files)
                print_statistics()
                input("\nPress Enter to continue...")
            else:
                print("  Cancelled.")

        elif choice == '2':
            list_files()
            input("\nPress Enter to continue...")

        elif choice == '3':
            view_output()
            input("\nPress Enter to continue...")

        elif choice == '4':
            system_check()
            input("\nPress Enter to continue...")

        elif choice == '5':
            clear_rips_folder()
            input("\nPress Enter to continue...")

        elif choice == '6':
            show_about()
            input("\nPress Enter to continue...")

        elif choice == '0':
            print("\n  Thanks for using RAVEDUMP RIPPER!")
            print("  Goodbye.\n")
            break

        else:
            print("\n  ✗ Invalid option. Please try again.")
            time.sleep(1)


if __name__ == "__main__":
    main()
