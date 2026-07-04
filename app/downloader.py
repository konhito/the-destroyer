from __future__ import annotations

import logging
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.config import ChannelPairConfig
from app.exceptions import NonRetriableError
from app.models import DownloadResult, VideoCandidate


class YtDlpDownloader:
    def __init__(
        self,
        downloads_dir: Path,
        logger: logging.Logger,
        *,
        cookies_file: Path | None = None,
        js_runtime: str | None = None,
        remote_components: str | None = None,
    ) -> None:
        self._downloads_dir = downloads_dir
        self._logger = logger
        self._cookies_file = cookies_file
        self._js_runtime = js_runtime
        self._remote_components = remote_components
        self._downloads_dir.mkdir(parents=True, exist_ok=True)

    def download(self, channel: ChannelPairConfig, video: VideoCandidate) -> DownloadResult:
        output_template = str(self._downloads_dir / f"{channel.name}-%(id)s.%(ext)s")
        opts = {
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "restrictfilenames": True,
            "merge_output_format": "mp4",
        }
        if self._cookies_file:
            opts["cookiefile"] = str(self._cookies_file)
        if self._js_runtime:
            opts["js_runtimes"] = {self._js_runtime: None}
        if self._remote_components:
            opts["remote_components"] = [self._remote_components]
        try:
            with YoutubeDL(opts) as ydl:
                metadata = ydl.extract_info(video.webpage_url, download=True)
                file_path = Path(ydl.prepare_filename(metadata))
                requested_downloads = metadata.get("requested_downloads") or []
                if requested_downloads and requested_downloads[0].get("filepath"):
                    file_path = Path(requested_downloads[0]["filepath"])
                if metadata.get("ext") and file_path.suffix.lower() != f".{metadata['ext'].lower()}":
                    candidate = file_path.with_suffix(f".{metadata['ext']}")
                    if candidate.exists():
                        file_path = candidate
        except DownloadError as exc:
            message = str(exc).lower()
            if any(token in message for token in ("private video", "video unavailable", "deleted", "members-only")):
                raise NonRetriableError(str(exc)) from exc
            raise

        self._logger.info(
            "Downloaded source_video_id=%s to %s",
            video.video_id,
            file_path,
        )
        return DownloadResult(video=video, file_path=file_path, source_metadata=metadata)
