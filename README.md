# RAVEDUMP RIPPER

Advanced audio extraction and recovery tool for video files.

## Features

- **Interactive CLI Menu** - Easy-to-use menu system for all operations
- **ASCII Art Banner** - Stylish RAVEDUMP RIPPER branding
- **Real-time Progress Bars** - Live progress tracking during extraction
- **Detailed Statistics** - Comprehensive stats after each rip session
- **Multiple Video Formats** - Supports MP4, AVI, MKV, MOV, FLV, WMV, WebM, M4V, MPG
- **Broken File Recovery** - Handles corrupted/broken video files
- **Smart Codec Detection** - Fast copy when possible, re-encode when needed
- **File Management** - Browse, list, and manage source/output files

## Requirements

- Python 3.6+
- ffmpeg
- tqdm (Python package)

### Installation

**1. Install ffmpeg:**

Ubuntu/Debian:
```bash
sudo apt-get install ffmpeg
```

MacOS:
```bash
brew install ffmpeg
```

Windows:
Download from https://ffmpeg.org/download.html

**2. Install Python dependencies:**
```bash
pip3 install -r requirements.txt
```

Or manually:
```bash
pip3 install tqdm
```

## Usage

1. **Place video files** in the `To_Rip/` folder

2. **Run the script:**
```bash
python3 audio_ripper.py
```

3. **Use the interactive menu:**
   - Option 1: Start ripping (process all files)
   - Option 2: List files in To_Rip folder
   - Option 3: View output in Rips folder
   - Option 4: System check (verify ffmpeg, directories)
   - Option 5: Clear Rips folder
   - Option 6: About
   - Option 0: Exit

4. **Check your output** - Extracted audio files are saved in `Rips/` folder as `.aac` files

## Menu Options Explained

### 1. Start Ripping
- Processes all video files in To_Rip folder
- Shows real-time progress bars
- Displays file-by-file status
- Provides detailed statistics upon completion

### 2. List Files
- Shows all video files in To_Rip folder
- Displays file sizes
- Shows video duration when available

### 3. View Output
- Lists all extracted audio files
- Shows file sizes
- Displays creation timestamps

### 4. System Check
- Verifies ffmpeg installation
- Checks directory structure
- Confirms Python dependencies

### 5. Clear Rips Folder
- Safely delete all files in output folder
- Requires confirmation before deletion

### 6. About
- Shows version and feature information

## Progress Tracking

During ripping, you'll see:
- **Overall progress bar** - Total files processed
- **File-by-file progress** - Current file being ripped
- **Real-time percentage** - Progress through each file
- **Method indicator** - Shows if using COPY or RE-ENC
- **Status updates** - Success/failure for each file

## Statistics

After ripping completes, detailed stats include:
- Total files processed
- Success/failure counts and percentages
- Extraction methods used (copy vs re-encode)
- Total input/output sizes
- Compression ratio
- Time elapsed
- Average time per file

## How It Works

1. **Scan** - Detects all video files in To_Rip folder
2. **Extract** - Uses ffmpeg with error recovery options
3. **Smart Processing:**
   - First attempts to copy audio stream (fast, no quality loss)
   - Falls back to re-encoding if copy fails
   - Handles broken files with error detection bypass
4. **Progress** - Real-time monitoring of extraction progress
5. **Output** - Saves AAC audio files to Rips folder

## Supported Formats

- MP4 (H.264, AAC)
- AVI
- MKV
- MOV
- FLV
- WMV
- WebM
- M4V
- MPG/MPEG

## Technical Details

### Fast Copy Mode
- Uses `-acodec copy` to extract audio without re-encoding
- Preserves original audio quality
- Very fast processing
- Used when audio codec is compatible

### Re-encode Mode
- Automatic fallback when copy fails
- Encodes to AAC at 192kbps, 44.1kHz
- Ensures compatibility
- Used for broken files or incompatible codecs

### Error Recovery
- `-err_detect ignore_err` - Ignores errors in broken files
- `-fflags +genpts` - Generates timestamps for corrupted files
- 5-minute timeout per file to prevent hangs

## Tips

- For best performance, ensure source files have AAC audio (enables fast copy mode)
- Large files may take longer to process
- Broken/corrupted files will automatically use recovery mode
- Check system requirements with menu option 4
- Use option 2 to preview files before ripping

## Troubleshooting

**"ffmpeg not found"**
- Install ffmpeg using instructions above
- Verify with: `ffmpeg -version`

**"tqdm not installed"**
- Install with: `pip3 install tqdm`

**Files not processing**
- Check file formats are supported
- Verify files are in To_Rip folder
- Run system check (menu option 4)

**Slow processing**
- Some files may require re-encoding
- Broken files take longer to process
- Check system resources

## Version

RAVEDUMP RIPPER v2.0

## License

Open source - Use freely
