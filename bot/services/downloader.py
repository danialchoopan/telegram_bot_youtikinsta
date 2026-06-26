import os
import yt_dlp
from bot.config import Config
from bot.utils.helpers import generate_random_string


class Downloader:
    def __init__(self):
        Config.ensure_directories()

    def download(self, url: str, format_type: str, progress_callback=None) -> tuple[str, dict]:
        filename = f"dl_{generate_random_string(12)}"
        ydl_opts = self._build_opts(format_type, filename)

        if progress_callback:
            ydl_opts["progress_hooks"] = [lambda d: self._progress_hook(d, progress_callback)]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = self._find_file(filename)
                if not file_path:
                    raise FileNotFoundError("Downloaded file not found")
                return file_path, info
        except Exception as e:
            self._cleanup(filename)
            raise

    def get_info_only(self, url: str) -> dict:
        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _build_opts(self, format_type: str, filename: str) -> dict:
        outtmpl = str(Config.DOWNLOAD_PATH / f"{filename}.%(ext)s")

        base_opts = {
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }

        if format_type == "mp3":
            return {
                **base_opts,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

        if format_type == "m4a":
            return {
                **base_opts,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": "128",
                }],
            }

        if format_type == "mkv":
            height = self._get_height_for_format(format_type)
            return {
                **base_opts,
                "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
                "merge_output_format": "mkv",
            }

        if format_type == "mp4_720":
            return {
                **base_opts,
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "merge_output_format": "mp4",
            }

        if format_type == "best":
            return {
                **base_opts,
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "merge_output_format": "mp4",
                "format_sort": ["res:1080", "codec:h264", "size"],
            }

        height = self._get_height_for_format(format_type)
        return {
            **base_opts,
            "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
            "merge_output_format": "mp4",
        }

    def _get_height_for_format(self, format_type: str) -> int:
        mapping = {"mp4": 1080, "mkv": 1080, "mp4_720": 720}
        return mapping.get(format_type, Config.MAX_RESOLUTION)

    def _progress_hook(self, data: dict, callback):
        if data["status"] == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            current = data.get("downloaded_bytes", 0)
            speed = data.get("speed") or 0
            eta = data.get("eta") or 0
            percent = (current / total * 100) if total > 0 else 0
            callback({
                "stage": "downloading",
                "percent": round(percent, 1),
                "current": current,
                "total": total,
                "speed": speed,
                "eta": eta,
            })
        elif data["status"] == "finished":
            callback({"stage": "download_complete"})

    def _find_file(self, filename_prefix: str) -> str | None:
        for f in os.listdir(Config.DOWNLOAD_PATH):
            if f.startswith(filename_prefix):
                return str(Config.DOWNLOAD_PATH / f)
        return None

    def _cleanup(self, filename_prefix: str):
        for f in os.listdir(Config.DOWNLOAD_PATH):
            if f.startswith(filename_prefix):
                os.remove(str(Config.DOWNLOAD_PATH / f))
