"""
==========================================
  Quality Optimizer Service
==========================================

Tactical FFmpeg-based optimizer for Telegram platform.

Strategy (in order of preference):
    1. Remux (instant, lossless) - if codecs already compatible
    2. Hardware-accelerated encode (CUDA/QSV/VAAPI) - if available
    3. Software encode (libx264) - universal fallback

FFmpeg principles:
    - Always test with -ss first before full encode
    - Use -c copy when possible (remux = instant)
    - -movflags +faststart for web streaming
    - -pix_fmt yuv420p for max player compatibility
    - CRF 22 = sweet spot (18=lossless, 23=default, 28=small)
"""

import os
import json
import time
import logging
import subprocess
from pathlib import Path

from bot.config import Config
from bot.utils.helpers import generate_random_string

logger = logging.getLogger(__name__)


class QualityOptimizer:
    """
    Tactical media optimizer for Telegram.

    Tries remux first, then hardware accel, then software encode.
    """

    def __init__(self):
        Config.ensure_directories()
        self.ffmpeg = Config.FFMPEG_PATH
        self._hw_accel = None  # Cached HW accel result

    def optimize(self, file_path: str, format_type: str, progress_callback=None) -> str:
        """
        Optimize media file for Telegram.

        Strategy:
            1. If already optimal format -> skip
            2. If codecs compatible -> remux (instant, lossless)
            3. Otherwise -> re-encode (HW accel if available, else SW)
        """
        logger.info(f"Optimizing: {file_path} -> {format_type}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Skip if already optimized
        if self._is_already_optimized(file_path, format_type):
            logger.info("Already optimized, skipping")
            return file_path

        ext = self._get_output_ext(format_type)
        output_path = str(Config.OPTIMIZED_PATH / f"opt_{generate_random_string(10)}{ext}")

        start_time = time.time()

        if format_type in ("mp3", "m4a"):
            self._optimize_audio(file_path, output_path, format_type)
        else:
            # Try remux first (instant, lossless)
            if self._try_remux(file_path, output_path, format_type):
                logger.info("Remux successful (instant, lossless)")
            else:
                # Re-encode with best available method
                hw = self._detect_hw_accel()
                if hw:
                    logger.info(f"Using hardware acceleration: {hw}")
                    self._encode_hw(file_path, output_path, format_type, hw)
                else:
                    logger.info("Using software encode (libx264)")
                    self._encode_sw(file_path, output_path, format_type)

        elapsed = time.time() - start_time
        logger.info(f"Optimization completed in {elapsed:.1f}s")

        # Verify output
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("Optimization failed: output file is empty or missing")

        original_size = os.path.getsize(file_path)
        optimized_size = os.path.getsize(output_path)

        if optimized_size > original_size:
            logger.info(f"Optimized larger than original, using original")
            os.remove(output_path)
            return file_path

        reduction = round((1 - optimized_size / original_size) * 100, 1) if original_size > 0 else 0
        logger.info(f"Result: {original_size} -> {optimized_size} bytes ({reduction}% reduction)")
        return output_path

    # ==========================================
    # Remux (instant, lossless)
    # ==========================================

    def _try_remux(self, input_path: str, output_path: str, format_type: str) -> bool:
        """
        Try remux (copy streams without re-encoding).
        Instant and lossless if codecs are compatible.
        """
        info = self._probe_file(input_path)
        if not info:
            return False

        # Check if video codec is already H.264
        video_codec = info.get("video_codec", "")
        audio_codec = info.get("audio_codec", "")
        is_h264 = video_codec in ("h264", "avc1")
        has_audio = audio_codec not in ("", "none")

        # For MP4: need H.264 video + AAC audio
        if format_type in ("mp4", "best"):
            if is_h264 and audio_codec in ("aac", "mp4a"):
                return self._remux(input_path, output_path)

        # For MKV: H.264 video is enough
        if format_type == "mkv":
            if is_h264:
                return self._remux(input_path, output_path)

        return False

    def _remux(self, input_path: str, output_path: str) -> bool:
        """Execute remux (copy streams)."""
        cmd = [
            self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", input_path,
            "-c", "copy",
            "-map", "0",
            "-avoid_negative_ts", "make_zero",
            output_path,
        ]
        try:
            self._run_ffmpeg(cmd)
            return True
        except Exception as e:
            logger.warning(f"Remux failed: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False

    # ==========================================
    # Hardware Acceleration Detection
    # ==========================================

    def _detect_hw_accel(self) -> str | None:
        """Detect available hardware acceleration."""
        if self._hw_accel is not None:
            return self._hw_accel

        try:
            result = subprocess.run(
                [self.ffmpeg, "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=5,
            )
            encoders = result.stdout

            # Check in priority order
            if "h264_nvenc" in encoders:
                self._hw_accel = "cuda"
            elif "h264_qsv" in encoders:
                self._hw_accel = "qsv"
            elif "h264_vaapi" in encoders:
                self._hw_accel = "vaapi"
            else:
                self._hw_accel = None

            logger.info(f"HW accel detected: {self._hw_accel or 'none'}")
            return self._hw_accel
        except Exception:
            self._hw_accel = None
            return None

    # ==========================================
    # Hardware-Accelerated Encoding
    # ==========================================

    def _encode_hw(self, input_path: str, output_path: str, format_type: str, hw_type: str):
        """Encode using hardware acceleration."""
        if hw_type == "cuda":
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-hwaccel", "cuda",
                "-i", input_path,
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                output_path,
            ]
        elif hw_type == "qsv":
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-hwaccel", "qsv",
                "-i", input_path,
                "-c:v", "h264_qsv",
                "-global_quality", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                output_path,
            ]
        elif hw_type == "vaapi":
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi",
                "-i", input_path,
                "-c:v", "h264_vaapi",
                "-qp", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                output_path,
            ]
        else:
            self._encode_sw(input_path, output_path, format_type)
            return

        try:
            self._run_ffmpeg(cmd)
        except Exception as e:
            logger.warning(f"HW encode failed ({hw_type}): {e}, falling back to SW")
            self._encode_sw(input_path, output_path, format_type)

    # ==========================================
    # Software Encoding (universal fallback)
    # ==========================================

    def _encode_sw(self, input_path: str, output_path: str, format_type: str):
        """Encode using software (libx264) - works everywhere."""
        if format_type == "mkv":
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", input_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "slow",
                "-crf", "21",
                "-maxrate", "6M",
                "-bufsize", "12M",
                "-movflags", "+faststart",
                output_path,
            ]
        else:
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", input_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-preset", Config.OPTIMIZATION_PRESET,
                "-crf", "22",
                "-maxrate", f"{Config.VIDEO_BITRATE_MBPS}M",
                "-bufsize", f"{Config.VIDEO_BITRATE_MBPS * 2}M",
                "-movflags", "+faststart",
                output_path,
            ]

        self._run_ffmpeg(cmd)

    # ==========================================
    # Audio Optimization
    # ==========================================

    def _optimize_audio(self, input_path: str, output_path: str, format_type: str):
        """Optimize audio with loudness normalization."""
        if format_type == "mp3":
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", input_path,
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", "192k",
                "-ar", "44100",
                "-ac", "2",
                "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
                output_path,
            ]
        else:  # m4a
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", input_path,
                "-vn",
                "-acodec", "aac",
                "-ab", "128k",
                "-ar", "44100",
                "-ac", "2",
                "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
                output_path,
            ]

        self._run_ffmpeg(cmd)

    # ==========================================
    # File Probing & Info
    # ==========================================

    def _probe_file(self, file_path: str) -> dict | None:
        """Probe file to get codec info using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                file_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return None

            data = json.loads(result.stdout)
            streams = data.get("streams", [])

            video_codec = ""
            audio_codec = ""
            width = 0
            height = 0

            for s in streams:
                if s.get("codec_type") == "video":
                    video_codec = s.get("codec_name", "")
                    width = int(s.get("width", 0))
                    height = int(s.get("height", 0))
                elif s.get("codec_type") == "audio":
                    audio_codec = s.get("codec_name", "")

            fmt = data.get("format", {})
            return {
                "video_codec": video_codec,
                "audio_codec": audio_codec,
                "width": width,
                "height": height,
                "duration": float(fmt.get("duration", 0)),
                "size": int(fmt.get("size", 0)),
            }
        except Exception as e:
            logger.error(f"Probe failed: {e}")
            return None

    def _is_already_optimized(self, file_path: str, format_type: str) -> bool:
        """Check if file is already in optimal format."""
        if format_type in ("mp3", "m4a"):
            return file_path.endswith(f".{format_type}")

        info = self._probe_file(file_path)
        if not info:
            # If we can't probe, check extension only
            return file_path.endswith(".mp4")

        # Already H.264 - skip re-encoding regardless of container
        if info["video_codec"] in ("h264", "avc1"):
            logger.info(f"File already H.264 ({info['video_codec']}), skipping optimization")
            return True

        return False

    # ==========================================
    # FFmpeg Execution
    # ==========================================

    def _run_ffmpeg(self, cmd: list):
        """Execute ffmpeg with timeout and clean error reporting."""
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            _, stderr = process.communicate(timeout=Config.MAX_OPTIMIZATION_TIME_SECONDS)

            if process.returncode != 0:
                # Clean error: skip banner lines
                error_lines = [
                    line for line in stderr.split('\n')
                    if line.strip()
                    and not line.startswith('ffmpeg')
                    and not line.startswith('built')
                    and not line.startswith('configuration')
                    and not line.startswith('  ')
                ]
                error_msg = '\n'.join(error_lines[-5:]) if error_lines else stderr[-500:]
                logger.error(f"FFmpeg failed (code {process.returncode}): {error_msg}")
                raise RuntimeError(f"FFmpeg error: {error_msg}")

            logger.info("FFmpeg completed successfully")

        except subprocess.TimeoutExpired:
            process.kill()
            logger.error("FFmpeg timed out")
            raise RuntimeError("Optimization timed out")

    # ==========================================
    # Helpers
    # ==========================================

    def _get_output_ext(self, format_type: str) -> str:
        ext_map = {"mp4": ".mp4", "mkv": ".mkv", "mp3": ".mp3", "m4a": ".m4a", "best": ".mp4"}
        return ext_map.get(format_type, ".mp4")

    def extract_thumbnail(self, file_path: str) -> str | None:
        """Extract thumbnail using -ss before -i (fast seek)."""
        if not Config.ENABLE_THUMBNAIL_EXTRACTION:
            return None
        thumb_path = str(Config.OPTIMIZED_PATH / f"thumb_{generate_random_string(8)}.jpg")
        try:
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-ss", "00:00:01",
                "-i", file_path,
                "-frames:v", "1",
                "-vf", "scale=320:-1",
                thumb_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=15)
            if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
                return thumb_path
        except Exception:
            pass
        return None
