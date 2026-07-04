from __future__ import annotations

import json
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from app.config import ChannelPairConfig, UploadDefaultsConfig
from app.exceptions import NonRetriableError
from app.models import DownloadResult, UploadPayload, UploadResult

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _is_retriable_upload_error(exc: HttpError) -> bool:
    status = getattr(exc.resp, "status", None)
    if status in {429, 500, 502, 503, 504}:
        return True
    if status != 403:
        return False
    message = ""
    try:
        payload = json.loads(exc.content.decode("utf-8"))
        reasons = payload.get("error", {}).get("errors", [])
        message = " ".join(
            str(item.get("reason", ""))
            for item in reasons
            if isinstance(item, dict)
        )
    except Exception:
        message = str(exc)
    return any(token in message for token in ("rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded", "backendError"))


def _close_media_upload(media_upload) -> None:
    file_descriptor = getattr(media_upload, "_fd", None)
    if file_descriptor and not getattr(file_descriptor, "closed", False):
        file_descriptor.close()


class YouTubeUploadClient:
    def __init__(self, defaults: UploadDefaultsConfig, logger: logging.Logger) -> None:
        self._defaults = defaults
        self._logger = logger

    def upload(self, channel: ChannelPairConfig, download_result: DownloadResult) -> UploadResult:
        credentials = self._load_credentials(
            channel.target_client_secret_json,
            channel.target_oauth_token_json,
        )
        service = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        payload = self._build_payload(channel, download_result)
        media_upload = MediaFileUpload(
            str(download_result.file_path),
            chunksize=self._defaults.chunk_size_bytes,
            resumable=True,
        )
        request = service.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": payload.title,
                    "description": payload.description,
                    "tags": payload.tags,
                    "categoryId": payload.category_id,
                },
                "status": {
                    "privacyStatus": payload.privacy_status,
                },
            },
            media_body=media_upload,
        )

        response = None
        try:
            while response is None:
                _, response = request.next_chunk()
        except HttpError as exc:
            if _is_retriable_upload_error(exc):
                raise
            raise NonRetriableError(str(exc)) from exc
        finally:
            _close_media_upload(media_upload)

        uploaded_video_id = response["id"]
        uploaded_url = f"https://www.youtube.com/watch?v={uploaded_video_id}"
        self._logger.info(
            "Uploaded source_video_id=%s to target_video_id=%s",
            download_result.video.video_id,
            uploaded_video_id,
        )
        return UploadResult(video_id=uploaded_video_id, title=payload.title, url=uploaded_url)

    def _load_credentials(self, client_secret_path: Path, token_path: Path) -> Credentials:
        credentials: Credentials | None = None
        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(str(token_path), YOUTUBE_SCOPES)
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            token_path.write_text(credentials.to_json(), encoding="utf-8")
            return credentials
        if credentials and credentials.valid:
            return credentials
        if not client_secret_path.exists():
            raise NonRetriableError(f"Missing OAuth client secret: {client_secret_path}")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), YOUTUBE_SCOPES)
        credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def _build_payload(self, channel: ChannelPairConfig, download_result: DownloadResult) -> UploadPayload:
        original_title = download_result.video.title.strip()
        description = "".join(
            [
                self._defaults.description_prefix,
                channel.description_prefix,
                (download_result.video.description or "").strip(),
                channel.description_suffix,
                self._defaults.description_suffix,
            ]
        ).strip()
        title = f"{self._defaults.title_prefix}{channel.title_prefix}{original_title}".strip()
        tags = [*self._defaults.tags, *channel.tags]
        return UploadPayload(
            title=title[:100],
            description=description[:5000],
            tags=tags[:500],
            privacy_status=self._defaults.privacy_status,
            category_id=self._defaults.category_id,
        )
