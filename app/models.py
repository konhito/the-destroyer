from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class VideoCandidate:
    video_id: str
    title: str
    webpage_url: str
    channel_name: str | None = None
    upload_date: str | None = None
    description: str | None = None


@dataclass(slots=True)
class UploadResult:
    video_id: str
    title: str
    url: str


@dataclass(slots=True)
class UploadPayload:
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    privacy_status: str = "private"
    category_id: str = "22"


@dataclass(slots=True)
class DownloadResult:
    video: VideoCandidate
    file_path: Path
    source_metadata: dict


@dataclass(slots=True)
class VideoProcessResult:
    channel_name: str
    source_video_id: str
    status: str
    upload_video_id: str | None = None
    local_file_path: str | None = None
    error_message: str | None = None
    download_attempts: int = 0
    upload_attempts: int = 0
