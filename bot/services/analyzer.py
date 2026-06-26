import yt_dlp
from bot.config import Config
from bot.utils.helpers import detect_platform


class MediaAnalyzer:
    def __init__(self):
        self.ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

    def get_info(self, url: str) -> dict:
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._format_info(info, url)
        except Exception as e:
            raise ValueError(f"Could not analyze link: {str(e)}")

    def _format_info(self, info: dict, url: str) -> dict:
        platform = detect_platform(url)
        title = info.get("title", "Unknown")
        duration = info.get("duration", 0)
        thumbnail = info.get("thumbnail", None)

        formats = info.get("formats", [])
        original_height = 0
        original_size = 0
        available_resolutions = set()

        for f in formats:
            height = f.get("height")
            if height:
                available_resolutions.add(height)
                if height > original_height:
                    original_height = height
            filesize = f.get("filesize") or f.get("filesize_approx")
            if filesize and filesize > original_size:
                original_size = filesize

        available_resolutions = sorted(available_resolutions, reverse=True)

        has_video = any(f.get("vcodec") and f["vcodec"] != "none" for f in formats)
        has_audio = any(f.get("acodec") and f["acodec"] != "none" for f in formats)

        if has_video and has_audio:
            media_type = "video"
        elif has_audio:
            media_type = "audio"
        else:
            media_type = "unknown"

        is_4k = original_height >= 2160

        return {
            "url": url,
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "platform": platform,
            "media_type": media_type,
            "original_height": original_height,
            "original_size": original_size,
            "available_resolutions": available_resolutions,
            "is_4k": is_4k,
            "formats_available": self._get_format_options(media_type, original_height),
        }

    def _get_format_options(self, media_type: str, max_height: int) -> list:
        if media_type == "audio":
            return ["mp3", "m4a"]

        options = []
        capped_height = min(max_height, Config.MAX_RESOLUTION) if Config.ENABLE_4K_BLOCKING else max_height

        if capped_height >= 1080:
            options.append(("mp4", "📹 MP4 1080p"))
            options.append(("mkv", "🎬 MKV 1080p"))
        if capped_height >= 720:
            options.append(("mp4_720", "📹 MP4 720p"))
        options.append(("mp3", "🎵 MP3 Audio"))
        options.append(("m4a", "🎶 M4A Audio"))
        options.append(("best", "⚡ Best for Telegram"))

        return options

    def check_4k(self, url: str) -> bool:
        if not Config.ENABLE_4K_BLOCKING:
            return False
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                for f in info.get("formats", []):
                    height = f.get("height", 0)
                    if height >= 2160:
                        return True
                return False
        except Exception:
            return False

    def estimate_size(self, url: str, format_type: str) -> int:
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if format_type in ("mp3", "m4a"):
                    duration = info.get("duration", 0)
                    bitrate = 192 if format_type == "mp3" else 128
                    return int(duration * bitrate * 1000 / 8)

                best_size = 0
                for f in info.get("formats", []):
                    if f.get("vcodec") and f["vcodec"] != "none":
                        height = f.get("height", 0)
                        if height <= Config.MAX_RESOLUTION:
                            size = f.get("filesize") or f.get("filesize_approx") or 0
                            if size > best_size:
                                best_size = size
                return best_size
        except Exception:
            return 0
