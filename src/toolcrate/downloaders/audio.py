import logging
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)


class AudioDownloader:
    """High-quality audio downloader for YouTube and SoundCloud."""

    def __init__(self, output_path: str = "downloads", quality: str = "320"):
        """
        Initialize the audio downloader.

        Args:
            output_path: Base directory to save downloaded files
            quality: Audio quality in kbps (default: "320")
        """
        self.base_output_path = Path(output_path).expanduser()
        self.quality = quality

    def _get_playlist_info(self, url: str, platform: str) -> tuple[str, bool]:  # noqa: ARG002
        """
        Extract playlist name and check if URL is a playlist.

        Args:
            url: URL to check
            platform: Either "youtube" or "soundcloud"

        Returns:
            Tuple of (playlist_name, is_playlist)
        """
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if "entries" in info:  # It's a playlist
                    playlist_name = info.get("title", "Unknown Playlist")
                    return playlist_name, True
                else:  # Single track
                    return info.get("title", "Unknown Track"), False
        except Exception as e:
            logger.error(f"Failed to get playlist info: {e}")
            return "Unknown", False

    def _get_output_path(self, url: str, platform: str) -> Path:
        """
        Determine the output path based on whether it's a playlist or single track.

        Args:
            url: URL to download
            platform: Either "youtube" or "soundcloud"

        Returns:
            Path object for the output directory
        """
        playlist_name, is_playlist = self._get_playlist_info(url, platform)
        if is_playlist:
            # Create a sanitized playlist name for the directory
            safe_name = "".join(
                c for c in playlist_name if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            return self.base_output_path / safe_name
        else:
            return self.base_output_path

    def _ensure_output_directory(self, path: Path) -> None:
        """Create output directory if it doesn't exist."""
        path.mkdir(parents=True, exist_ok=True)

    def _get_ydl_opts(self, platform: str, output_path: Path) -> dict[str, Any]:  # noqa: ARG002
        """
        Get yt-dlp options for downloading.

        Args:
            platform: Either "youtube" or "soundcloud"
            output_path: Path to save files

        Returns:
            Dictionary of yt-dlp options
        """
        return {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": self.quality,
                }
            ],
            "outtmpl": str(output_path / "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
        }

    def download_youtube(self, url: str) -> Path | None:
        """
        Download audio from YouTube URL.

        Args:
            url: YouTube video or playlist URL

        Returns:
            Path to downloaded file(s) or None if download failed
        """
        logger.info(f"🎥 Downloading from YouTube: {url}")
        try:
            output_path = self._get_output_path(url, "youtube")
            self._ensure_output_directory(output_path)

            ydl_opts = self._get_ydl_opts("youtube", output_path)
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if "entries" in info:  # Playlist
                    num_tracks = len(
                        [entry for entry in info["entries"] if entry is not None]
                    )
                    logger.info(
                        f"✅ Successfully downloaded playlist with {num_tracks} tracks"
                    )
                    return output_path
                else:  # Single video
                    title = info.get("title", "Unknown Title")
                    logger.info(f"✅ Successfully downloaded: {title}")
                    return output_path / f"{title}.mp3"
        except Exception as e:
            logger.error(f"❌ Failed to download from YouTube {url}: {e}")
            return None

    def download_soundcloud(self, url: str) -> Path | None:
        """
        Download audio from SoundCloud URL.

        Args:
            url: SoundCloud track or playlist URL

        Returns:
            Path to downloaded file(s) or None if download failed
        """
        logger.info(f"🎵 Downloading from SoundCloud: {url}")
        try:
            output_path = self._get_output_path(url, "soundcloud")
            self._ensure_output_directory(output_path)

            ydl_opts = self._get_ydl_opts("soundcloud", output_path)
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if "entries" in info:  # Playlist
                    num_tracks = len(
                        [entry for entry in info["entries"] if entry is not None]
                    )
                    logger.info(
                        f"✅ Successfully downloaded playlist with {num_tracks} tracks"
                    )
                    return output_path
                else:  # Single track
                    title = info.get("title", "Unknown Title")
                    logger.info(f"✅ Successfully downloaded: {title}")
                    return output_path / f"{title}.mp3"
        except Exception as e:
            logger.error(f"❌ Failed to download from SoundCloud {url}: {e}")
            return None

    def download(self, url: str) -> Path | None:
        """
        Download audio from YouTube or SoundCloud URL.

        Args:
            url: URL to download from

        Returns:
            Path to downloaded file(s) or None if download failed
        """
        url_lower = url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return self.download_youtube(url)
        elif "soundcloud.com" in url_lower:
            return self.download_soundcloud(url)
        else:
            logger.error(
                "❌ Unsupported URL format. Please provide a YouTube or SoundCloud link."
            )
            return None
