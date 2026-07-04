from __future__ import annotations

import logging
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.config import ChannelPairConfig, DiscoveryConfig
from app.exceptions import NonRetriableError
from app.models import VideoCandidate


class YtDlpDiscoveryClient:
    def __init__(
        self,
        config: DiscoveryConfig,
        logger: logging.Logger,
        *,
        cookies_file: Path | None = None,
        js_runtime: str | None = None,
        remote_components: str | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._cookies_file = cookies_file
        self._js_runtime = js_runtime
        self._remote_components = remote_components

    def list_videos(self, channel: ChannelPairConfig) -> list[VideoCandidate]:
        opts = {
            "extract_flat": True,
            "skip_download": True,
            "playlistend": self._config.max_candidates,
            "quiet": True,
            "ignoreerrors": True,
        }
        if self._cookies_file:
            opts["cookiefile"] = str(self._cookies_file)
        if self._js_runtime:
            opts["js_runtimes"] = {self._js_runtime: None}
        if self._remote_components:
            opts["remote_components"] = self._remote_components
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
