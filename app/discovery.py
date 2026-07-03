from __future__ import annotations

import logging

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.config import ChannelPairConfig, DiscoveryConfig
from app.exceptions import NonRetriableError
from app.models import VideoCandidate


class YtDlpDiscoveryClient:
    def __init__(self, config: DiscoveryConfig, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger

    def list_videos(self, channel: ChannelPairConfig) -> list[VideoCandidate]:
        opts = {
            "extract_flat": True,
            "skip_download": True,
            "playlistend": self._config.max_candidates,
            "quiet": True,
            "ignoreerrors": True,
        }
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(channel.source_url, download=False)
        except DownloadError as exc:
            message = str(exc).lower()
            if any(token in message for token in ("private", "deleted", "unavailable", "404")):
                raise NonRetriableError(str(exc)) from exc
            raise

        entries = info.get("entries", []) if isinstance(info, dict) else []
        videos: list[VideoCandidate] = []
        for entry in entries:
            if not entry:
                continue
            video_id = entry.get("id")
            title = entry.get("title") or "Untitled video"
            if not video_id:
                continue
            videos.append(
                VideoCandidate(
                    video_id=video_id,
                    title=title,
                    webpage_url=entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
                    channel_name=entry.get("channel") or channel.source_channel_label,
                    upload_date=entry.get("upload_date"),
                    description=entry.get("description"),
                )
            )
        self._logger.info("Discovered %s candidate videos for %s", len(videos), channel.name)
        return videos
