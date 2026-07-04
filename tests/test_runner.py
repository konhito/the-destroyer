from __future__ import annotations

import logging
from pathlib import Path

from app.config import (
    AppConfig,
    ChannelPairConfig,
    DatabaseConfig,
    DiscoveryConfig,
    PathsConfig,
    RetryConfig as AppRetryConfig,
    UploadDefaultsConfig,
    YtDlpConfig,
)
from app.exceptions import RetryExhaustedError
from app.files import FileManager
from app.models import DownloadResult, UploadResult, VideoCandidate
from app.runner import VideoAutomationRunner


class FakeRepository:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def is_processed_successfully(self, source_video_id: str, target_channel_name: str) -> bool:
        return False

    def upsert_video_record(self, **kwargs) -> None:
        self.records.append(kwargs)


class FakeDiscovery:
    def __init__(self, calls: list[str], videos: list[VideoCandidate]) -> None:
        self.calls = calls
        self.videos = videos

    def list_videos(self, channel) -> list[VideoCandidate]:
        self.calls.append("discover")
        return self.videos


class FakeDownloader:
    def __init__(self, calls: list[str], file_path: Path) -> None:
        self.calls = calls
        self.file_path = file_path

    def download(self, channel, video: VideoCandidate) -> DownloadResult:
        self.calls.append("download")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text("video-bytes", encoding="utf-8")
        return DownloadResult(video=video, file_path=self.file_path, source_metadata={})


class FakeUploader:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def upload(self, channel, download_result: DownloadResult) -> UploadResult:
        self.calls.append("upload")
        return UploadResult(
            video_id="uploaded123",
            title=download_result.video.title,
            url="https://www.youtube.com/watch?v=uploaded123",
        )


class FailingUploader:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.attempts = 0

    def upload(self, channel, download_result: DownloadResult) -> UploadResult:
        self.calls.append("upload")
        self.attempts += 1
        raise RuntimeError("upload failed")


class TrackingFileManager(FileManager):
    def __init__(self, failed_dir: Path, calls: list[str]) -> None:
        super().__init__(failed_dir)
        self.calls = calls

    def delete_file(self, path: Path) -> None:
        self.calls.append("delete")
        super().delete_file(path)

    def move_to_failed(self, path: Path) -> Path:
        self.calls.append("move-failed")
        return super().move_to_failed(path)


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        database=DatabaseConfig(dsn="postgresql://unused"),
        retry=AppRetryConfig(max_attempts=2, initial_delay_seconds=0, backoff_multiplier=1, max_delay_seconds=0),
        discovery=DiscoveryConfig(latest_only=True, max_candidates=10),
        paths=PathsConfig(
            downloads_dir=tmp_path / "downloads",
            failed_dir=tmp_path / "failed",
            logs_dir=tmp_path / "logs",
        ),
        ytdlp=YtDlpConfig(),
        upload_defaults=UploadDefaultsConfig(),
        channel_pairs=[
            ChannelPairConfig(
                name="pair-01",
                enabled=True,
                source_url="https://youtube.com/@source/videos",
                source_channel_label="Source",
                target_channel_name="Target",
                target_client_secret_json=tmp_path / "client.json",
                target_oauth_token_json=tmp_path / "token.json",
            )
        ],
    )


def test_runner_processes_one_video_in_order(tmp_path: Path) -> None:
    calls: list[str] = []
    config = make_config(tmp_path)
    video = VideoCandidate(
        video_id="abc123",
        title="Video Title",
        webpage_url="https://www.youtube.com/watch?v=abc123",
        channel_name="Source",
    )
    repository = FakeRepository()
    runner = VideoAutomationRunner(
        config=config,
        repository=repository,
        discovery=FakeDiscovery(calls, [video]),
        downloader=FakeDownloader(calls, tmp_path / "downloads" / "abc123.mp4"),
        uploader=FakeUploader(calls),
        file_manager=TrackingFileManager(tmp_path / "failed", calls),
        logger=logging.getLogger("test-runner-success"),
    )

    processed = runner.run()

    assert processed == 1
    assert calls == ["discover", "download", "upload", "delete"]
    assert repository.records[0]["result"].status == "success"


def test_runner_moves_failed_file_after_retries_exhausted(tmp_path: Path) -> None:
    calls: list[str] = []
    config = make_config(tmp_path)
    video = VideoCandidate(
        video_id="abc123",
        title="Video Title",
        webpage_url="https://www.youtube.com/watch?v=abc123",
        channel_name="Source",
    )
    repository = FakeRepository()
    runner = VideoAutomationRunner(
        config=config,
        repository=repository,
        discovery=FakeDiscovery(calls, [video]),
        downloader=FakeDownloader(calls, tmp_path / "downloads" / "abc123.mp4"),
        uploader=FailingUploader(calls),
        file_manager=TrackingFileManager(tmp_path / "failed", calls),
        logger=logging.getLogger("test-runner-failure"),
    )

    processed = runner.run()

    assert processed == 1
    assert calls == ["discover", "download", "upload", "upload", "move-failed"]
    assert repository.records[0]["result"].status == "failed"
    assert Path(repository.records[0]["result"].local_file_path).exists()
