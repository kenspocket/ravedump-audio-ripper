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
    print("❌ ERROR: tqdm not installed. Install with: pip3 install tqdm")
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
║                ██████╔╝██║██████╔╝██████╔╝█████╗  ██████╔╝                  ║
║                ██╔══██╗██║██╔═══╝ ██╔═══╝ ██╔══╝  ██╔══██╗                  ║
║                ██║  ██║██║██║     ██║     ███████╗██║  ██║                  ║
║                ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝     ╚══════╝╚═╝  ╚═╝                  ║
║                                                                              ║
║              4ud10 3xtr4ct10n & R3c0v3ry T00l v2.1 - Pr0p3r L33t           ║
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
        print(f"⚠️  Couldn't save config bruv: {e}")


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
    progress_bar.set_description(f"🎵 [R1PP1NG] {display_name}")

    # Show full path in console
    print(f"\n📂 Source: {input_file.absolute()}")
    print(f"📂 Dest:   {output_file.absolute()}")

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
                    progress_bar.set_postfix(progress=f"{percent:.1f}%", method="C0PY")
                except:
                    pass

        process.wait(timeout=config.get('timeout', 300))

        if process.returncode == 0 and output_file.exists():
            progress_bar.set_postfix(status="✅ C0P13D", size=format_size(get_file_size(output_file)))
            stats['copied'] += 1
            return True, 'copy'
        else:
            # Try re-encoding
            progress_bar.set_description(f"🔄 [R3-3NC] {display_name}")
            return extract_audio_reencode(input_file, output_file, progress_bar, config)

    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        progress_bar.set_postfix(status="❌ T1M30UT")
        return False, 'failed'
    except Exception as e:
        progress_bar.set_postfix(status=f"❌ 3RR0R")
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
                    progress_bar.set_postfix(progress=f"{percent:.1f}%", method="R3-3NC")
                except:
                    pass

        process.wait(timeout=config.get('timeout', 300))

        if process.returncode == 0 and output_file.exists():
            progress_bar.set_postfix(status="✅ R3-3NC0D3D", size=format_size(get_file_size(output_file)))
            stats['reencoded'] += 1
            return True, 'reencode'
        else:
            progress_bar.set_postfix(status="❌ F41L3D")
            return False, 'failed'

    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        progress_bar.set_postfix(status="❌ T1M30UT")
        return False, 'failed'
    except Exception as e:
        progress_bar.set_postfix(status="❌ 3RR0R")
        return False, 'failed'


def process_files(video_files: List[Path], config: Dict):
    """Process all video files with progress bars"""
    stats['start_time'] = time.time()
    stats['total_files'] = len(video_files)

    print("\n" + "═" * 80)
    print("🚀 ST4RT1NG R1P PR0C3SS - L3T'S 4V3 1T! 🚀")
    print("═" * 80 + "\n")

    # Main progress bar for overall progress
    with tqdm(total=len(video_files),
              desc="📊 [0V3R4LL]",
              unit=" fil3",
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
    print("🎉 R1P C0MPL3T3 - CH3CK TH3 ST4TS M8! 🎉")
    print("═" * 80)
    print(f"📦 Total Fil3s:        {stats['total_files']}")
    print(f"  ✅ Succ3ssful:       {stats['successful']} ({stats['successful']/stats['total_files']*100:.1f}%)")
    print(f"  ❌ F41l3d:           {stats['failed']}")
    print(f"\n🔧 3xtr4ct10n M3th0ds:")
    print(f"  ⚡ F4st C0py:        {stats['copied']}")
    print(f"  🔄 R3-3nc0d3d:       {stats['reencoded']}")
    print(f"\n💾 D4t4 Pr0c3ss3d:")
    print(f"  📥 Input S1z3:       {format_size(stats['total_size_input'])}")
    print(f"  📤 0utput S1z3:      {format_size(stats['total_size_output'])}")

    if stats['total_size_input'] > 0:
        compression = (1 - stats['total_size_output'] / stats['total_size_input']) * 100
        print(f"  🗜️  C0mpr3ss10n:      {compression:.1f}%")

    print(f"\n⏱️  T1m3 3l4ps3d:       {format_time(duration)}")
    if duration > 0:
        avg_time = duration / stats['total_files']
        print(f"⏱️  4v3r4g3 p3r fil3:  {format_time(avg_time)}")

    print(f"\n📂 0utput D1r3ct0ry:   {DEST_DIR.absolute()}")
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
        print(f"📂 0p3n3d: {path.absolute()}")
    except Exception as e:
        print(f"⚠️  C0uldn't 0p3n f0ld3r bruv: {e}")


def list_files():
    """List all video files in To_Rip folder"""
    video_files = get_video_files()

    if not video_files:
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║  ❌ N0 F1L3S F0UND - 3MPTY INN1T!                              ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"\n📂 Source Path: {SOURCE_DIR.absolute()}")
        print(f"📋 Supp0rt3d f0rm4ts: {', '.join(sorted(VIDEO_EXTENSIONS))}")
        print("\n💡 Dr0p s0m3 vid30s in th3r3 m8!")
        return

    print("\n╔════════════════════════════════════════════════════════════════╗")
    print(f"║  📼 F1L3S 1N T0_R1P F0LD3R: {len(video_files)} fil3(s)")
    print("╚════════════════════════════════════════════════════════════════╝")
    print(f"\n📂 Full Path: {SOURCE_DIR.absolute()}\n")

    total_size = 0
    for i, file_path in enumerate(video_files, 1):
        size = get_file_size(file_path)
        total_size += size
        duration = get_video_duration(file_path)
        dur_str = f" ⏱️ [{format_time(duration)}]" if duration else ""
        print(f"  {i:2d}. 📹 {file_path.name[:45]:45s} 💾 {format_size(size):>10s}{dur_str}")

    print(f"\n  📦 T0t4l s1z3: {format_size(total_size)}")


def view_output():
    """View files in Rips folder"""
    output_files = sorted([f for f in DEST_DIR.iterdir() if f.is_file()])

    if not output_files:
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║  ❌ N0 0UTPUT F1L3S - N0TH1N' R1PP3D Y3T!                      ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"\n📂 Output Path: {DEST_DIR.absolute()}")
        print("\n💡 R1p s0m3 tun3s f1rst bruv!")
        return

    print("\n╔════════════════════════════════════════════════════════════════╗")
    print(f"║  🎵 F1L3S 1N R1PS F0LD3R: {len(output_files)} fil3(s)")
    print("╚════════════════════════════════════════════════════════════════╝")
    print(f"\n📂 Full Path: {DEST_DIR.absolute()}\n")

    total_size = 0
    for i, file_path in enumerate(output_files, 1):
        size = get_file_size(file_path)
        total_size += size
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        print(f"  {i:2d}. 🎵 {file_path.name[:45]:45s} 💾 {format_size(size):>10s}  📅 [{mod_time}]")

    print(f"\n  📦 T0t4l s1z3: {format_size(total_size)}")


def show_menu():
    """Display CLI menu"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║               🎛️  M41N M3NU - CH00S3 Y3R 0PT10N 🎛️               ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print("║  1️⃣  - ST4RT R1PP1NG (pr0c3ss 4ll fil3s innit)                  ║")
    print("║  2️⃣  - L1ST F1L3S (ch3ck wh4t's in T0_R1p)                      ║")
    print("║  3️⃣  - V13W 0UTPUT (p33k 4t y3r r1pp3d tun3s)                   ║")
    print("║  4️⃣  - SYST3M CH3CK (v3r1fy th3 t3ch)                           ║")
    print("║  5️⃣  - CL34R R1PS (d3l3t3 0utput fil3s)                         ║")
    print("║  6️⃣  - S3TT1NGS (tw34k th3 c0nf1g)                              ║")
    print("║  7️⃣  - 4B0UT (pr0p3r 1nf0)                                      ║")
    print("║  0️⃣  - 3X1T (b4il 0ut)                                          ║")
    print("╚════════════════════════════════════════════════════════════════╝")


def system_check():
    """Check system requirements"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║  🔧 SYST3M CH3CK - T3ST1NG TH3 K1T 🔧                          ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    # Check ffmpeg
    if check_ffmpeg():
        print("  ✅ ffmpeg inst4ll3d - w1ck3d!")
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            version_line = result.stdout.split('\n')[0]
            print(f"    ℹ️  {version_line}")
        except:
            pass
    else:
        print("  ❌ ffmpeg N0T inst4ll3d - s0rt 1t 0ut m8!")
        print("    💡 Inst4ll: sudo apt-get install ffmpeg")

    # Check directories
    print(f"\n  📂 D1r3ct0r13s:")
    print(f"    Source:      {SOURCE_DIR.absolute()} {'✅' if SOURCE_DIR.exists() else '❌'}")
    print(f"    Destination: {DEST_DIR.absolute()} {'✅' if DEST_DIR.exists() else '❌'}")
    print(f"    Config:      {CONFIG_DIR.absolute()} {'✅' if CONFIG_DIR.exists() else '❌'}")

    # Check Python version
    print(f"\n  🐍 Pyth0n:      {sys.version.split()[0]} ✅")

    # Check tqdm
    print(f"  📊 tqdm:        Inst4ll3d ✅")

    # Platform
    print(f"  💻 Pl4tf0rm:    {platform.system()} {platform.release()}")


def clear_rips_folder():
    """Clear all files in Rips folder"""
    output_files = list(DEST_DIR.glob('*'))
    output_files = [f for f in output_files if f.is_file()]

    if not output_files:
        print("\n  ℹ️  R1ps f0ld3r 1s 4lr34dy 3mpty innit.")
        return

    print(f"\n  📂 Full Path: {DEST_DIR.absolute()}")
    print(f"  ⚠️  F0und {len(output_files)} fil3(s) in R1ps f0ld3r.")
    confirm = input("  ❓ D3l3t3 4ll fil3s? (y3s/n0): ").strip().lower()

    if confirm == 'yes' or confirm == 'y':
        deleted = 0
        for file_path in output_files:
            try:
                file_path.unlink()
                deleted += 1
            except:
                print(f"  ❌ F41l3d t0 d3l3t3: {file_path.name}")
        print(f"  ✅ D3l3t3d {deleted} fil3(s) - 4ll cl34n bruv!")
    else:
        print("  ❌ C4nc3ll3d - k33p1ng y3r fil3s.")


def show_settings(config: Dict):
    """Show and modify settings"""
    while True:
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║              ⚙️  S3TT1NGS - TW34K TH3 C0NF1G ⚙️                  ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"\n📂 C0nf1g Path: {CONFIG_FILE.absolute()}\n")
        print(f"  1️⃣  - 4ud10 B1tr4t3:      {config.get('audio_bitrate', '192k')}")
        print(f"  2️⃣  - S4mpl3 R4t3:        {config.get('sample_rate', '44100')} Hz")
        print(f"  3️⃣  - 0utput F0rm4t:      {config.get('output_format', 'aac')}")
        print(f"  4️⃣  - T1m30ut:            {config.get('timeout', 300)}s")
        print(f"  5️⃣  - 4ut0 0p3n F0ld3r:   {'Y3s ✅' if config.get('auto_open_folder', False) else 'N0 ❌'}")
        print(f"\n  9️⃣  - R3S3T T0 D3F4ULTS")
        print(f"  0️⃣  - B4CK T0 M41N M3NU")

        choice = input("\n  ❓ S3l3ct 0pt10n: ").strip()

        if choice == '1':
            bitrate = input("  💿 3nt3r 4ud10 b1tr4t3 (3.g. 192k, 256k, 320k): ").strip()
            if bitrate:
                config['audio_bitrate'] = bitrate
                save_config(config)
                print(f"  ✅ 4ud10 b1tr4t3 s3t t0: {bitrate}")

        elif choice == '2':
            rate = input("  🎚️  3nt3r s4mpl3 r4t3 (3.g. 44100, 48000): ").strip()
            if rate.isdigit():
                config['sample_rate'] = rate
                save_config(config)
                print(f"  ✅ S4mpl3 r4t3 s3t t0: {rate} Hz")

        elif choice == '3':
            fmt = input("  📝 3nt3r 0utput f0rm4t (4ac, mp3, 0gg): ").strip().lower()
            if fmt in ['aac', 'mp3', 'ogg']:
                config['output_format'] = fmt
                save_config(config)
                print(f"  ✅ 0utput f0rm4t s3t t0: {fmt}")

        elif choice == '4':
            timeout = input("  ⏱️  3nt3r t1m30ut in s3c0nds (3.g. 300): ").strip()
            if timeout.isdigit():
                config['timeout'] = int(timeout)
                save_config(config)
                print(f"  ✅ T1m30ut s3t t0: {timeout}s")

        elif choice == '5':
            auto = input("  📂 4ut0 0p3n f0ld3r 4ft3r r1pp1ng? (y3s/n0): ").strip().lower()
            config['auto_open_folder'] = (auto == 'yes' or auto == 'y')
            save_config(config)
            status = "3n4bl3d ✅" if config['auto_open_folder'] else "d1s4bl3d ❌"
            print(f"  ✅ 4ut0 0p3n f0ld3r {status}")

        elif choice == '9':
            confirm = input("  ⚠️  R3s3t 4ll s3tt1ngs t0 d3f4ults? (y3s/n0): ").strip().lower()
            if confirm == 'yes' or confirm == 'y':
                config.update(DEFAULT_CONFIG)
                save_config(config)
                print("  ✅ S3tt1ngs r3s3t t0 d3f4ults!")

        elif choice == '0':
            print("  ⬅️  B4ck t0 m41n m3nu...")
            break

        else:
            print("  ❌ 1nv4l1d 0pt10n - try 4g41n bruv!")

        time.sleep(1)


def show_about():
    """Show about information"""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║  🎉 R4V3DUMP R1PP3R v2.1 - PR0P3R L33T 🎉                      ║")
    print("╠════════════════════════════════════════════════════════════════╣")
    print("║  4dv4nc3d 4ud10 3xtr4ct10n t00l f0r vid30 fil3s               ║")
    print("║                                                                ║")
    print("║  ✨ F34tur3s:                                                  ║")
    print("║  🎵 3xtr4ct 4ud10 fr0m 4ny vid30 f0rm4t                       ║")
    print("║  🔧 H4ndl3 br0k3n/c0rrupt3d fil3s l1k3 4 b0ss                 ║")
    print("║  ⚡ Sm4rt c0d3c d3t3ct10n 4nd c0py1ng                         ║")
    print("║  🔄 4ut0m4t1c f4llb4ck t0 r3-3nc0d1ng                         ║")
    print("║  📊 R34l-t1m3 pr0gr3ss tr4ck1ng                               ║")
    print("║  📈 D3t41l3d st4t1st1cs 4nd 4n4lyt1cs                         ║")
    print("║  ⚙️  C0nf1gur4bl3 s3tt1ngs 1n /c0nf1g/                        ║")
    print("║  🎛️  1nt3r4ct1v3 CL1 w1th pr0p3r sl4ng                        ║")
    print("║                                                                ║")
    print("║  📼 Supp0rts: MP4, 4V1, MKV, M0V, FLV, WMV, W3bM, M4V, MPG    ║")
    print("║                                                                ║")
    print("║  💾 C0d3d w1th pr0p3r l33t sp34k 4nd c0ckn3y sl4ng m8!        ║")
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
        print("\n❌ 3RR0R: ffmpeg 41n't inst4ll3d bruv!")
        print("📥 Pl34s3 inst4ll ffmpeg:")
        print("  🐧 Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  🍎 MacOS: brew install ffmpeg")
        print("  🪟 Windows: Download from https://ffmpeg.org/download.html")
        input("\n⏎  Pr3ss 3nt3r t0 3x1t...")
        sys.exit(1)

    while True:
        show_menu()
        choice = input("\n  ❓ S3l3ct 0pt10n: ").strip()

        if choice == '1':
            video_files = get_video_files()
            if not video_files:
                print("\n  ❌ N0 vid30 fil3s f0und in T0_R1p f0ld3r!")
                print(f"  📂 Path: {SOURCE_DIR.absolute()}")
                print("  💡 4dd s0m3 vid30s 4nd try 4g41n m8!")
                input("\n  ⏎  Pr3ss 3nt3r t0 c0nt1nu3...")
                continue

            print(f"\n  📦 F0und {len(video_files)} fil3(s) r34dy t0 r1p.")
            print(f"  📂 Source: {SOURCE_DIR.absolute()}")
            print(f"  📂 Dest:   {DEST_DIR.absolute()}")
            confirm = input("  ❓ ST4RT R1PP1NG? (y3s/n0): ").strip().lower()

            if confirm == 'yes' or confirm == 'y':
                process_files(video_files, config)
                print_statistics()

                # Ask to open folder
                if config.get('auto_open_folder', False):
                    open_choice = 'y'
                else:
                    open_choice = input("  📂 0p3n R1ps f0ld3r? (y/n): ").strip().lower()

                if open_choice == 'y' or open_choice == 'yes':
                    open_folder(DEST_DIR)

                input("\n  ⏎  Pr3ss 3nt3r t0 c0nt1nu3...")
            else:
                print("  ❌ C4nc3ll3d - n0 w0rr13s bruv.")

        elif choice == '2':
            list_files()
            input("\n  ⏎  Pr3ss 3nt3r t0 c0nt1nu3...")

        elif choice == '3':
            view_output()
            open_choice = input("\n  📂 0p3n R1ps f0ld3r? (y/n): ").strip().lower()
            if open_choice == 'y' or open_choice == 'yes':
                open_folder(DEST_DIR)
            input("\n  ⏎  Pr3ss 3nt3r t0 c0nt1nu3...")

        elif choice == '4':
            system_check()
            input("\n  ⏎  Pr3ss 3nt3r t0 c0nt1nu3...")

        elif choice == '5':
            clear_rips_folder()
            input("\n  ⏎  Pr3ss 3nt3r t0 c0nt1nu3...")

        elif choice == '6':
            show_settings(config)

        elif choice == '7':
            show_about()
            input("\n  ⏎  Pr3ss 3nt3r t0 c0nt1nu3...")

        elif choice == '0':
            print("\n  👋 Ch33rs f0r us1ng R4V3DUMP R1PP3R!")
            print("  🎵 K33p r1pp1ng th0s3 tun3s bruv!")
            print("  ✌️  L4t3rs! ✌️\n")
            break

        else:
            print("\n  ❌ 1nv4l1d 0pt10n - try 4g41n m8!")
            time.sleep(1)


if __name__ == "__main__":
    main()
