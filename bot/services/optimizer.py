"""
==========================================
  Quality Optimizer Service
==========================================

Optimizes media files for Telegram's platform using ffmpeg.
Handles video/audio encoding, compression, and format conversion.

Optimization Features:
    - H.264 video encoding (best Telegram compatibility)
    - AAC audio encoding
    - Resolution capping (max 1080p)
    - Bitrate control for consistent file sizes
    - Audio normalization (ReplayGain)
    - Fast-start flag for streaming

Video Settings (MP4):
    - Codec: H.264 (libx264)
    - Pixel format: yuv420p
    - CRF: 23 (good quality/size balance)
    - Max bitrate: 4 Mbps
    - Preset: medium (configurable)

Audio Settings (MP3/M4A):
    - MP3: 192kbps CBR, stereo, 44.1kHz
    - M4A: 128kbps AAC, stereo, 44.1kHz
    - Normalization: loudnorm filter

Usage:
    optimizer = QualityOptimizer()
    optimized_path = optimizer.optimize(file_path, "mp4")
"""

import os
import time
import subprocess
import shutil
from pathlib import Path

from bot.config import Config
from bot.utils.helpers import generate_random_string


class QualityOptimizer:
    """
    Media optimizer for Telegram platform.

    Uses ffmpeg to re-encode and compress media files
    for optimal quality and file size on Telegram.
    """

    def __init__(self):
        """Initialize optimizer with ffmpeg path."""
        Config.ensure_directories()
        self.ffmpeg = Config.FFMPEG_PATH

    def optimize(self, file_path: str, format_type: str, progress_callback=None) -> str:
        """
        Optimize a media file for Telegram.

        Args:
            file_path: Path to input file
            format_type: Output format (mp4, mkv, mp3, m4a)
            progress_callback: Optional callback for progress updates

        Returns:
            str: Path to optimized file (or original if already optimized)

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If optimization fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Skip optimization if file is already in optimal format
        if self._is_already_optimized(file_path, format_type):
            return file_path

        # Generate output path
        ext = self._get_output_ext(format_type)
        output_path = str(Config.OPTIMIZED_PATH / f"opt_{generate_random_string(10)}{ext}")

        start_time = time.time()

        # Run appropriate optimization based on format
        if format_type in ("mp3", "m4a"):
            self._optimize_audio(file_path, output_path, format_type, progress_callback)
        else:
            self._optimize_video(file_path, output_path, format_type, progress_callback)

        elapsed = time.time() - start_time

        # Verify output file exists and has content
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("Optimization failed: output file is empty or missing")

        # If optimized file is larger, use original
        original_size = os.path.getsize(file_path)
        optimized_size = os.path.getsize(output_path)
        if optimized_size > original_size:
            os.remove(output_path)
            return file_path

        return output_path

    def _optimize_video(self, input_path: str, output_path: str, format_type: str, progress_callback=None):
        """
        Optimize video for Telegram using ffmpeg.

        Uses H.264 encoding with CRF for consistent quality.
        Caps resolution at 1080p and controls bitrate.
        """
        # MKV uses slightly different settings
        if format_type == "mkv":
            settings = {
                "vcodec": "libx264",
                "acodec": "aac",
                "pix_fmt": "yuv420p",
                "preset": "slow",           # Better quality for MKV
                "crf": 21,                  # Higher quality than MP4
                "maxrate": "6M",
                "bufsize": "12M",
                "vf": "scale=min(1920,iw):-2",  # Cap at 1080p width
            }
        else:
            # MP4 settings optimized for Telegram
            settings = {
                "vcodec": "libx264",        # H.264 for compatibility
                "acodec": "aac",            # AAC audio
                "pix_fmt": "yuv420p",       # Standard pixel format
                "movflags": "+faststart",   # Enable streaming
                "preset": Config.OPTIMIZATION_PRESET,
                "crf": 23,                  # Good quality/size balance
                "maxrate": f"{Config.VIDEO_BITRATE_MBPS}M",
                "bufsize": f"{Config.VIDEO_BITRATE_MBPS * 2}M",
                "vf": "scale=min(1920,iw):-2",  # Cap at 1080p width
                "profile:v": "high",        # H.264 High profile
                "level": "4.0",             # Compatibility level
            }

        # Build ffmpeg command
        cmd = [
            self.ffmpeg, "-y", "-i", input_path,
            "-vcodec", settings["vcodec"],
            "-acodec", settings["acodec"],
            "-pix_fmt", settings["pix_fmt"],
            "-preset", settings["preset"],
            "-crf", str(settings["crf"]),
            "-maxrate", settings["maxrate"],
            "-bufsize", settings["bufsize"],
            "-vf", settings["vf"],
            "-profile:v", settings["profile:v"],
            "-level", settings["level"],
        ]

        # Add faststart flag if present
        if settings.get("movflags"):
            cmd.extend(["-movflags", settings["movflags"]])

        cmd.append(output_path)
        self._run_ffmpeg(cmd, progress_callback)

    def _optimize_audio(self, input_path: str, output_path: str, format_type: str, progress_callback=None):
        """
        Optimize audio for Telegram.

        Applies loudness normalization and sets consistent bitrate.
        """
        if format_type == "mp3":
            # MP3: 192kbps CBR, stereo, 44.1kHz with normalization
            cmd = [
                self.ffmpeg, "-y", "-i", input_path,
                "-acodec", "libmp3lame",
                "-ab", "192k",              # 192kbps bitrate
                "-ar", "44100",             # 44.1kHz sample rate
                "-ac", "2",                 # Stereo
                "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",  # EBU R128 normalization
                output_path,
            ]
        else:
            # M4A: 128kbps AAC, stereo, 44.1kHz with normalization
            cmd = [
                self.ffmpeg, "-y", "-i", input_path,
                "-acodec", "aac",
                "-ab", "128k",              # 128kbps bitrate
                "-ar", "44100",             # 44.1kHz sample rate
                "-ac", "2",                 # Stereo
                "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",  # EBU R128 normalization
                output_path,
            ]

        self._run_ffmpeg(cmd, progress_callback)

    def _run_ffmpeg(self, cmd: list, progress_callback=None):
        """
        Execute ffmpeg command with timeout.

        Args:
            cmd: ffmpeg command as list of arguments
            progress_callback: Optional callback (not used with subprocess)

        Raises:
            RuntimeError: If ffmpeg fails or times out
        """
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            # Wait for completion with timeout
            _, stderr = process.communicate(timeout=Config.MAX_OPTIMIZATION_TIME_SECONDS)
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {stderr[:500]}")
        except subprocess.TimeoutExpired:
            process.kill()
            raise RuntimeError("Optimization timed out")

    def _is_already_optimized(self, file_path: str, format_type: str) -> bool:
        """
        Check if file is already in optimal format.

        Returns True if:
        - Audio file already has correct extension
        - Video file is already H.264 MP4
        """
        if format_type in ("mp3", "m4a"):
            return file_path.endswith(f".{format_type}")
        return file_path.endswith(".mp4") and self._check_h264(file_path)

    def _check_h264(self, file_path: str) -> bool:
        """Check if video uses H.264 codec."""
        try:
            cmd = [
                self.ffmpeg, "-i", file_path,
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_name",
                "-v", "quiet",
                "-of", "csv=p=0",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return "h264" in result.stdout.lower()
        except Exception:
            return False

    def get_video_info(self, file_path: str) -> dict:
        """
        Get video file metadata.

        Returns:
            dict: width, height, codec, duration, size
        """
        try:
            cmd = [
                self.ffmpeg, "-i", file_path,
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,codec_name,duration",
                "-show_entries", "format=duration,size",
                "-v", "quiet",
                "-of", "json",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            import json
            data = json.loads(result.stdout)
            stream = data.get("streams", [{}])[0]
            fmt = data.get("format", {})
            return {
                "width": int(stream.get("width", 0)),
                "height": int(stream.get("height", 0)),
                "codec": stream.get("codec_name", "unknown"),
                "duration": float(fmt.get("duration", 0)),
                "size": int(fmt.get("size", 0)),
            }
        except Exception:
            return {"width": 0, "height": 0, "codec": "unknown", "duration": 0, "size": 0}

    def _get_output_ext(self, format_type: str) -> str:
        """Map format type to file extension."""
        ext_map = {"mp4": ".mp4", "mkv": ".mkv", "mp3": ".mp3", "m4a": ".m4a", "best": ".mp4"}
        return ext_map.get(format_type, ".mp4")

    def extract_thumbnail(self, file_path: str) -> str | None:
        """
        Extract thumbnail from video at 1 second mark.

        Returns:
            str: Path to thumbnail file, or None if extraction fails
        """
        if not Config.ENABLE_THUMBNAIL_EXTRACTION:
            return None
        thumb_path = str(Config.OPTIMIZED_PATH / f"thumb_{generate_random_string(8)}.jpg")
        try:
            cmd = [
                self.ffmpeg, "-y", "-i", file_path,
                "-ss", "00:00:01",          # Seek to 1 second
                "-vframes", "1",            # Extract single frame
                "-vf", "scale=320:-1",      # Resize to 320px width
                thumb_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=15)
            if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
                return thumb_path
        except Exception:
            pass
        return None
