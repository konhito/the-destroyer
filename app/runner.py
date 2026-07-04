from __future__ import annotations

import logging
from typing import Protocol

from app.config import AppConfig
from app.exceptions import NonRetriableError, RetryExhaustedError
from app.files import FileManager
from app.models import DownloadResult, UploadResult, VideoCandidate, VideoProcessResult
from app.retry import RetryConfig, run_with_retry


class VideoRepository(Protocol):
    def is_processed_successfully(self, source_video_id: str, target_channel_name: str) -> bool: ...

    def upsert_video_record(
        self,
        *,
        source_url: str,
        source_channel_label: str,
        result: VideoProcessResult,
        uploaded_url: str | None = None,
    ) -> None: ...


class DiscoveryClient(Protocol):
    def list_videos(self, channel) -> list[VideoCandidate]: ...


class Downloader(Protocol):
    def download(self, channel, video: VideoCandidate) -> DownloadResult: ...


class Uploader(Protocol):
    def upload(self, channel, download_result: DownloadResult) -> UploadResult: ...


class VideoAutomationRunner:
    def __init__(
        self,
        *,
        config: AppConfig,
        repository: VideoRepository,
        discovery: DiscoveryClient,
        downloader: Downloader,
        uploader: Uploader,
        file_manager: FileManager,
        logger: logging.Logger,
    ) -> None:
        self.config = config
        self.repository = repository
        self.discovery = discovery
        self.downloader = downloader
        self.uploader = uploader
        self.file_manager = file_manager
        self.logger = logger
        self.retry_config = RetryConfig(
            max_attempts=config.retry.max_attempts,
            initial_delay_seconds=config.retry.initial_delay_seconds,
            backoff_multiplier=config.retry.backoff_multiplier,
            max_delay_seconds=config.retry.max_delay_seconds,
        )

    def run(self) -> int:
        processed_count = 0
        for channel in self.config.enabled_channel_pairs():
            candidates = self.discovery.list_videos(channel)
            pending = [
                video
                for video in candidates
                if not self.repository.is_processed_successfully(video.video_id, channel.target_channel_name)
            ]
            if self.config.discovery.latest_only and pending:
                pending = pending[:1]
            for video in pending:
                self.process_video(channel, video)
                processed_count += 1
        return processed_count

    def process_video(self, channel, video: VideoCandidate) -> None:
        self.logger.info(
            "Starting source_video_id=%s source=%s target=%s",
            video.video_id,
            channel.source_channel_label,
            channel.target_channel_name,
        )
        download_result: DownloadResult | None = None
        download_attempts = 0
        upload_attempts = 0

        try:
            download_retry = run_with_retry(
                lambda: self.downloader.download(channel, video),
                self.retry_config,
            )
            download_result = download_retry.value
            download_attempts = download_retry.attempts

            upload_retry = run_with_retry(
                lambda: self.uploader.upload(channel, download_result),
                self.retry_config,
            )
            upload_attempts = upload_retry.attempts
            upload_result = upload_retry.value

            self.repository.upsert_video_record(
                source_url=video.webpage_url,
                source_channel_label=channel.source_channel_label,
                result=VideoProcessResult(
                    channel_name=channel.target_channel_name,
                    source_video_id=video.video_id,
                    status="success",
                    upload_video_id=upload_result.video_id,
                    local_file_path=str(download_result.file_path),
                    download_attempts=download_attempts,
                    upload_attempts=upload_attempts,
                ),
                uploaded_url=upload_result.url,
            )
            self.file_manager.delete_file(download_result.file_path)
            self.logger.info(
                "Completed source_video_id=%s target_video_id=%s",
                video.video_id,
                upload_result.video_id,
            )
        except NonRetriableError as exc:
            self._record_failure(channel, video, download_result, download_attempts, upload_attempts, str(exc))
        except RetryExhaustedError as exc:
            download_attempts = max(download_attempts, exc.attempts)
            stage = "download" if download_result is None else "upload"
            self.logger.exception(
                "%s failed after retries source_video_id=%s target=%s",
                stage.capitalize(),
                video.video_id,
                channel.target_channel_name,
            )
            self._record_failure(
                channel,
                video,
                download_result,
                download_attempts,
                upload_attempts,
                str(exc.last_error),
            )

    def _record_failure(
        self,
        channel,
        video: VideoCandidate,
        download_result: DownloadResult | None,
        download_attempts: int,
        upload_attempts: int,
        error_message: str,
    ) -> None:
        local_file_path = None
        if download_result and download_result.file_path.exists():
            moved_path = self.file_manager.move_to_failed(download_result.file_path)
            local_file_path = str(moved_path)
        self.repository.upsert_video_record(
            source_url=video.webpage_url,
            source_channel_label=channel.source_channel_label,
            result=VideoProcessResult(
                channel_name=channel.target_channel_name,
                source_video_id=video.video_id,
                status="failed",
                local_file_path=local_file_path,
                error_message=error_message,
                download_attempts=download_attempts,
                upload_attempts=upload_attempts,
            ),
        )
        self.logger.error(
            "Failed source_video_id=%s target=%s error=%s",
            video.video_id,
            channel.target_channel_name,
            error_message,
        )
