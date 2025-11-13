#!/usr/bin/env python3
"""
RAVEDUMP RIPPER - Audio Extraction Tool
Extracts audio from video files (including broken/corrupted files)
Reads from: ./To_Rip/
Saves to: ./Rips/
Config: ./config/
"""

import os
import subprocess
import sys
import time
import re
import json
import platform
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from datetime import datetime

try:
    from tqdm import tqdm
except ImportError:
    print("❌ ERROR: tqdm ain't installed mate!")
    print("📥 Install it with: pip3 install tqdm")
    print("\nCan't do much without it, innit?")
    sys.exit(1)

# Directories
SCRIPT_DIR = Path(__file__).parent.absolute()
SOURCE_DIR = SCRIPT_DIR / "To_Rip"
DEST_DIR = SCRIPT_DIR / "Rips"
CONFIG_DIR = SCRIPT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"

# Supported video extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}

# Default config
DEFAULT_CONFIG = {
    'audio_bitrate': '192k',
    'sample_rate': '44100',
    'output_format': 'aac',
    'timeout': 300,
    'auto_open_folder': False
}

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
║                ██████╗ ██║██████╔╝██████╔╝█████╗  ██████╔╝                  ║
║                ██╔══██╗██║██╔═══╝ ██╔═══╝ ██╔══╝  ██╔══██╗                  ║
║                ██║  ██║██║██║     ██║     ███████╗██║  ██║                  ║
║                ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝     ╚══════╝╚═╝  ╚═╝                  ║
║                                                                              ║
║              Audio Extraction & Recovery Tool v2.5 - Proper Sorted          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def create_directories():
    """Create source, destination and config directories if they don't exist"""
    SOURCE_DIR.mkdir(exist_ok=True)
    DEST_DIR.mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)


def load_config() -> Dict:
    """Load config from file or create default"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except:
            return DEFAULT_CONFIG
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config: Dict):
    """Save config to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"⚠️  Couldn't save the config, bruv: {e}")


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


def extract_audio_with_progress(input_file: Path, progress_bar: tqdm, config: Dict) -> Tuple[bool, str]:
    """
    Extract audio from video file using ffmpeg with progress monitoring
    Returns: (success, method) where method is 'copy', 'reencode', or 'failed'
    """
    output_ext = config.get('output_format', 'aac')
    output_file = DEST_DIR / f"{input_file.stem}.{output_ext}"

    # Update progress bar description
    display_name = input_file.name[:40] if len(input_file.name) > 40 else input_file.name
    progress_bar.set_description(f"🎵 [RIPPING] {display_name}")

    # Show full path in console
    print(f"\n📂 Source: {input_file.absolute()}")
    print(f"📂 Dest:   {output_file.absolute()}")

    # Get video duration for progress calculation
    duration = get_video_duration(input_file)

    # Try copying audio codec first (faster, innit)
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

        process.wait(timeout=config.get('timeout', 300))

        if process.returncode == 0 and output_file.exists():
            progress_bar.set_postfix(status="✅ COPIED", size=format_size(get_file_size(output_file)))
            stats['copied'] += 1
            return True, 'copy'
        else:
            # Try re-encoding - bit slower but gets the job done
            progress_bar.set_description(f"🔄 [RE-ENC] {display_name}")
            return extract_audio_reencode(input_file, output_file, progress_bar, config)

    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        progress_bar.set_postfix(status="❌ TIMEOUT")
        return False, 'failed'
    except Exception as e:
        progress_bar.set_postfix(status=f"❌ ERROR")
        return False, 'failed'


def extract_audio_reencode(input_file: Path, output_file: Path, progress_bar: tqdm, config: Dict) -> Tuple[bool, str]:
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
        '-b:a', config.get('audio_bitrate', '192k'),
        '-ar', config.get('sample_rate', '44100'),
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

        process.wait(timeout=config.get('timeout', 300))

        if process.returncode == 0 and output_file.exists():
            progress_bar.set_postfix(status="✅ RE-ENCODED", size=format_size(get_file_size(output_file)))
            stats['reencoded'] += 1
            return True, 'reencode'
        else:
            progress_bar.set_postfix(status="❌ FAILED")
            return False, 'failed'

    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        progress_bar.set_postfix(status="❌ TIMEOUT")
        return False, 'failed'
    except Exception as e:
        progress_bar.set_postfix(status="❌ ERROR")
        return False, 'failed'


def process_files(video_files: List[Path], config: Dict):
    """Process all video files with progress bars"""
    stats['start_time'] = time.time()
    stats['total_files'] = len(video_files)

    print("\n" + "═" * 80)
    print("🚀 STARTING RIP PROCESS - LET'S 'AVE IT THEN! 🚀")
    print("═" * 80 + "\n")

    # Main progress bar for overall progress
    with tqdm(total=len(video_files),
              desc="📊 [OVERALL]",
              unit=" file",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
              position=0) as pbar:

        for video_file in video_files:
            # Calculate input size
            input_size = get_file_size(video_file)
            stats['total_size_input'] += input_size

            # Process file
            success, method = extract_audio_with_progress(video_file, pbar, config)

            if success:
                stats['successful'] += 1
                output_file = DEST_DIR / f"{video_file.stem}.{config.get('output_format', 'aac')}"
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
    print("🎉 RIP COMPLETE - CHECK THE STATS, MATE! 🎉")
    print("═" * 80)
    print(f"📦 Total Files:        {stats['total_files']}")
    print(f"  ✅ Successful:       {stats['successful']} ({stats['successful']/stats['total_files']*100:.1f}%)")
    print(f"  ❌ Failed:           {stats['failed']}")
    print(f"\n🔧 Extraction Methods:")
    print(f"  ⚡ Fast Copy:        {stats['copied']}")
    print(f"  🔄 Re-encoded:       {stats['reencoded']}")
    print(f"\n💾 Data Processed:")
    print(f"  📥 Input Size:       {format_size(stats['total_size_input'])}")
    print(f"  📤 Output Size:      {format_size(stats['total_size_output'])}")

    if stats['total_size_input'] > 0:
        compression = (1 - stats['total_size_output'] / stats['total_size_input']) * 100
        print(f"  🗜️  Compression:      {compression:.1f}%")

    print(f"\n⏱️  Time Elapsed:       {format_time(duration)}")
    if duration > 0:
        avg_time = duration / stats['total_files']
        print(f"⏱️  Average per file:  {format_time(avg_time)}")

    print(f"\n📂 Output Directory:   {DEST_DIR.absolute()}")
    print("═" * 80 + "\n")


def open_folder(path: Path):
    """Open folder in file explorer"""
    try:
        system = platform.system()
        if system == 'Windows':
            os.startfile(str(path))
        elif system == 'Darwin':  # macOS
            subprocess.run(['open', str(path)])
        else:  # Linux
            subprocess.run(['xdg-open', str(path)])
        print(f"📂 Opened: {path.absolute()}")
    except Exception as e:
        print(f"⚠️  Couldn't open the folder, mate: {e}")
        print(f"📂 You'll 'ave to navigate there yourself: {path.absolute()}")


def list_files():
    """List all video files in To_Rip folder"""
    video_files = get_video_files()

    if not video_files:
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║  ❌ NO FILES FOUND - EMPTY INNIT!                              ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"\n📂 Source Path: {SOURCE_DIR.absolute()}")
        print(f"📋 Supported formats: {', '.join(sorted(VIDEO_EXTENSIONS))}")
        print("\n💡 Drop some videos in there, mate!")
        return

    print("\n╔════════════════════════════════════════════════════════════════╗")
    print(f"║  📼 FILES IN TO_RIP FOLDER: {len(video_files)} file(s)")
    print("╚════════════════════════════════════════════════════════════════╝")
    print(f"\n📂 Full Path: {SOURCE_DIR.absolute()}\n")

    total_size = 0
    for i, file_path in enumerate(video_files, 1):
        size = get_file_size(file_path)
        total_size += size
        duration = get_video_duration(file_path)
        dur_str = f" ⏱️ [{format_time(duration)}]" if duration else ""
        print(f"  {i:2d}. 📹 {file_path.name[:45]:45s} 💾 {format_size(size):>10s}{dur_str}")

    print(f"\n  📦 Total size: {format_size(total_size)}")


def view_output():
    """View files in Rips folder"""
    output_files = sorted([f for f in DEST_DIR.iterdir() if f.is_file()])

    if not output_files:
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║  ❌ NO OUTPUT FILES - NOTHING RIPPED YET!                      ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"\n📂 Output Path: {DEST_DIR.absolute()}")
        print("\n💡 Rip some tunes first, bruv!")
        return

    print("\n╔════════════════════════════════════════════════════════════════╗")
    print(f"║  🎵 FILES IN RIPS FOLDER: {len(output_files)} file(s)")
    print("╚════════════════════════════════════════════════════════════════╝")
    print(f"\n📂 Full Path: {DEST_DIR.absolute()}\n")

    total_size = 0
    for i, file_path in enumerate(output_files, 1):
        size = get_file_size(file_path)
        total_size += size
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        print(f"  {i:2d}. 🎵 {file_path.name[:45]:45s} 💾 {format_size(size):>10s}  📅 [{mod_time}]")

    print(f"\n  📦 Total size: {format_size(total_size)}")


def show_menu():
    """Display CLI menu"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║               🎛️  MAIN MENU - CHOOSE YOUR OPTION 🎛️               ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print("║  1️⃣  - START RIPPING (process all files innit)                  ║")
    print("║  2️⃣  - LIST FILES (check what's in To_Rip)                      ║")
    print("║  3️⃣  - VIEW OUTPUT (peek at your ripped tunes)                  ║")
    print("║  4️⃣  - SYSTEM CHECK (verify the tech)                           ║")
    print("║  5️⃣  - CLEAR RIPS (delete output files)                         ║")
    print("║  6️⃣  - SETTINGS (tweak the config)                              ║")
    print("║  7️⃣  - ABOUT (proper info)                                      ║")
    print("║  0️⃣  - EXIT (bail out)                                          ║")
    print("╚════════════════════════════════════════════════════════════════╝")


def system_check():
    """Check system requirements"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║  🔧 SYSTEM CHECK - TESTING THE KIT 🔧                          ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    # Check ffmpeg
    if check_ffmpeg():
        print("  ✅ ffmpeg installed - proper sorted!")
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            version_line = result.stdout.split('\n')[0]
            print(f"    ℹ️  {version_line}")
        except:
            pass
    else:
        print("  ❌ ffmpeg NOT installed - need to sort that, mate!")
        print("    💡 Install: sudo apt-get install ffmpeg")

    # Check directories
    print(f"\n  📂 Directories:")
    print(f"    Source:      {SOURCE_DIR.absolute()} {'✅' if SOURCE_DIR.exists() else '❌'}")
    print(f"    Destination: {DEST_DIR.absolute()} {'✅' if DEST_DIR.exists() else '❌'}")
    print(f"    Config:      {CONFIG_DIR.absolute()} {'✅' if CONFIG_DIR.exists() else '❌'}")

    # Check Python version
    print(f"\n  🐍 Python:      {sys.version.split()[0]} ✅")

    # Check tqdm
    print(f"  📊 tqdm:        Installed ✅")

    # Platform
    print(f"  💻 Platform:    {platform.system()} {platform.release()}")


def clear_rips_folder():
    """Clear all files in Rips folder"""
    output_files = list(DEST_DIR.glob('*'))
    output_files = [f for f in output_files if f.is_file()]

    if not output_files:
        print("\n  ℹ️  Rips folder is already empty, innit.")
        return

    print(f"\n  📂 Full Path: {DEST_DIR.absolute()}")
    print(f"  ⚠️  Found {len(output_files)} file(s) in Rips folder.")
    confirm = input("  ❓ Delete all files? (yes/no): ").strip().lower()

    if confirm == 'yes' or confirm == 'y':
        deleted = 0
        for file_path in output_files:
            try:
                file_path.unlink()
                deleted += 1
            except:
                print(f"  ❌ Failed to delete: {file_path.name}")
        print(f"  ✅ Deleted {deleted} file(s) - all clean, bruv!")
    else:
        print("  ❌ Cancelled - keeping your files then.")


def show_settings(config: Dict):
    """Show and modify settings"""
    while True:
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║              ⚙️  SETTINGS - TWEAK THE CONFIG ⚙️                  ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"\n📂 Config Path: {CONFIG_FILE.absolute()}\n")
        print(f"  1️⃣  - Audio Bitrate:      {config.get('audio_bitrate', '192k')}")
        print(f"  2️⃣  - Sample Rate:        {config.get('sample_rate', '44100')} Hz")
        print(f"  3️⃣  - Output Format:      {config.get('output_format', 'aac')}")
        print(f"  4️⃣  - Timeout:            {config.get('timeout', 300)}s")
        print(f"  5️⃣  - Auto Open Folder:   {'Yes ✅' if config.get('auto_open_folder', False) else 'No ❌'}")
        print(f"\n  9️⃣  - RESET TO DEFAULTS")
        print(f"  0️⃣  - BACK TO MAIN MENU")

        choice = input("\n  ❓ Select option: ").strip()

        if choice == '1':
            bitrate = input("  💿 Enter audio bitrate (e.g. 192k, 256k, 320k): ").strip()
            if bitrate:
                config['audio_bitrate'] = bitrate
                save_config(config)
                print(f"  ✅ Audio bitrate set to: {bitrate} - sorted!")

        elif choice == '2':
            rate = input("  🎚️  Enter sample rate (e.g. 44100, 48000): ").strip()
            if rate.isdigit():
                config['sample_rate'] = rate
                save_config(config)
                print(f"  ✅ Sample rate set to: {rate} Hz - nice one!")

        elif choice == '3':
            fmt = input("  📝 Enter output format (aac, mp3, ogg): ").strip().lower()
            if fmt in ['aac', 'mp3', 'ogg']:
                config['output_format'] = fmt
                save_config(config)
                print(f"  ✅ Output format set to: {fmt} - blinding!")

        elif choice == '4':
            timeout = input("  ⏱️  Enter timeout in seconds (e.g. 300): ").strip()
            if timeout.isdigit():
                config['timeout'] = int(timeout)
                save_config(config)
                print(f"  ✅ Timeout set to: {timeout}s - proper job!")

        elif choice == '5':
            auto = input("  📂 Auto open folder after ripping? (yes/no): ").strip().lower()
            config['auto_open_folder'] = (auto == 'yes' or auto == 'y')
            save_config(config)
            status = "enabled ✅" if config['auto_open_folder'] else "disabled ❌"
            print(f"  ✅ Auto open folder {status}")

        elif choice == '9':
            confirm = input("  ⚠️  Reset all settings to defaults? (yes/no): ").strip().lower()
            if confirm == 'yes' or confirm == 'y':
                config.update(DEFAULT_CONFIG)
                save_config(config)
                print("  ✅ Settings reset to defaults - back to basics!")

        elif choice == '0':
            print("  ⬅️  Back to main menu, mate...")
            break

        else:
            print("  ❌ Invalid option - try again, bruv!")

        time.sleep(1)


def show_about():
    """Show about information"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║  🎉 RAVEDUMP RIPPER v2.5 - PROPER SORTED 🎉                    ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print("║  Advanced audio extraction tool for video files               ║")
    print("║                                                                ║")
    print("║  ✨ Features:                                                  ║")
    print("║  🎵 Extract audio from any video format                       ║")
    print("║  🔧 Handle broken/corrupted files like a boss                 ║")
    print("║  ⚡ Smart codec detection and copying                         ║")
    print("║  🔄 Automatic fallback to re-encoding                         ║")
    print("║  📊 Real-time progress tracking                               ║")
    print("║  📈 Detailed statistics and analytics                         ║")
    print("║  ⚙️  Configurable settings in /config/                        ║")
    print("║  🎛️  Interactive CLI with proper slang                        ║")
    print("║                                                                ║")
    print("║  📼 Supports: MP4, AVI, MKV, MOV, FLV, WMV, WebM, M4V, MPG    ║")
    print("║                                                                ║")
    print("║  💾 Coded with proper cockney slang, innit!                   ║")
    print("╚════════════════════════════════════════════════════════════════╝")


def main():
    """Main function with CLI menu"""
    print_banner()

    # Create directories
    create_directories()

    # Load config
    config = load_config()

    # Check ffmpeg
    if not check_ffmpeg():
        print("\n❌ ERROR: ffmpeg ain't installed, mate!")
        print("📥 Please install ffmpeg:")
        print("  🐧 Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  🍎 MacOS: brew install ffmpeg")
        print("  🪟 Windows: Download from https://ffmpeg.org/download.html")
        print("\nCan't rip without it, innit?")
        input("\n⏎  Press Enter to exit...")
        sys.exit(1)

    while True:
        show_menu()
        choice = input("\n  ❓ Select option: ").strip()

        if choice == '1':
            video_files = get_video_files()
            if not video_files:
                print("\n  ❌ No video files found in To_Rip folder!")
                print(f"  📂 Path: {SOURCE_DIR.absolute()}")
                print("  💡 Add some videos and try again, mate!")
                input("\n  ⏎  Press Enter to continue...")
                continue

            print(f"\n  📦 Found {len(video_files)} file(s) ready to rip.")
            print(f"  📂 Source: {SOURCE_DIR.absolute()}")
            print(f"  📂 Dest:   {DEST_DIR.absolute()}")
            confirm = input("  ❓ START RIPPING? (yes/no): ").strip().lower()

            if confirm == 'yes' or confirm == 'y':
                process_files(video_files, config)
                print_statistics()

                # Ask to open folder
                if config.get('auto_open_folder', False):
                    open_choice = 'y'
                else:
                    open_choice = input("  📂 Open Rips folder? (y/n): ").strip().lower()

                if open_choice == 'y' or open_choice == 'yes':
                    open_folder(DEST_DIR)

                input("\n  ⏎  Press Enter to continue...")
            else:
                print("  ❌ Cancelled - no worries, bruv.")

        elif choice == '2':
            list_files()
            input("\n  ⏎  Press Enter to continue...")

        elif choice == '3':
            view_output()
            open_choice = input("\n  📂 Open Rips folder? (y/n): ").strip().lower()
            if open_choice == 'y' or open_choice == 'yes':
                open_folder(DEST_DIR)
            input("\n  ⏎  Press Enter to continue...")

        elif choice == '4':
            system_check()
            input("\n  ⏎  Press Enter to continue...")

        elif choice == '5':
            clear_rips_folder()
            input("\n  ⏎  Press Enter to continue...")

        elif choice == '6':
            show_settings(config)

        elif choice == '7':
            show_about()
            input("\n  ⏎  Press Enter to continue...")

        elif choice == '0':
            print("\n  👋 Cheers for using RAVEDUMP RIPPER!")
            print("  🎵 Keep ripping those tunes, mate!")
            print("  ✌️  Ta-ra! ✌️\n")
            break

        else:
            print("\n  ❌ Invalid option - try again, bruv!")
            time.sleep(1)


if __name__ == "__main__":
    main()
