# Audio Ripper

Extract audio from video files including broken or corrupted files.

## Features

- Extracts audio from various video formats (.mp4, .avi, .mkv, .mov, etc.)
- Handles broken/corrupted video files with error recovery
- Supports H.264 video with AAC audio streams
- Fast processing using ffmpeg audio codec copy
- Automatic fallback to re-encoding if needed

## Requirements

- Python 3.6+
- ffmpeg

### Installing ffmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**MacOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

## Usage

1. Place video files in the `To_Rip/` folder

2. Run the script:
```bash
python3 audio_ripper.py
```

3. Extracted audio files will be saved in the `Rips/` folder as `.aac` files

## How It Works

The script:
1. Scans the `To_Rip/` folder for video files
2. Uses ffmpeg to extract audio from each file
3. First attempts to copy the audio stream (fast, no quality loss)
4. Falls back to re-encoding if copying fails
5. Handles broken files with error recovery options
6. Saves extracted audio to `Rips/` folder

## Supported Formats

- MP4
- AVI
- MKV
- MOV
- FLV
- WMV
- WebM
- M4V
- MPG/MPEG

## Notes

- The script preserves the original filename (only changes extension to .aac)
- Existing files in the Rips folder will be overwritten
- Processing time depends on file size and whether re-encoding is needed
- Each file has a 5-minute timeout to prevent hanging on severely corrupted files
