from __future__ import annotations

import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.config import DatabaseConfig
from app.models import VideoProcessResult


class PostgresVideoRepository:
    def __init__(self, config: DatabaseConfig, logger: logging.Logger) -> None:
        self._dsn = config.dsn
        self._logger = logger

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def is_processed_successfully(self, source_video_id: str, target_channel_name: str) -> bool:
        query = """
        SELECT 1
        FROM processed_videos
        WHERE source_video_id = %s
          AND target_channel_name = %s
          AND status = 'success'
        LIMIT 1
        """
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, (source_video_id, target_channel_name))
            return cur.fetchone() is not None

    def upsert_video_record(
        self,
        *,
        source_url: str,
        source_channel_label: str,
        result: VideoProcessResult,
        uploaded_url: str | None = None,
    ) -> None:
        query = """
        INSERT INTO processed_videos (
            source_video_id,
            source_video_url,
            source_channel_label,
            target_channel_name,
            status,
            uploaded_video_id,
            uploaded_video_url,
            upload_title,
            local_file_path,
            error_message,
            download_attempts,
            upload_attempts
        ) VALUES (
            %(source_video_id)s,
            %(source_video_url)s,
            %(source_channel_label)s,
            %(target_channel_name)s,
            %(status)s,
            %(uploaded_video_id)s,
            %(uploaded_video_url)s,
            %(upload_title)s,
            %(local_file_path)s,
            %(error_message)s,
            %(download_attempts)s,
            %(upload_attempts)s
        )
        ON CONFLICT (source_video_id, target_channel_name)
        DO UPDATE SET
            status = EXCLUDED.status,
            uploaded_video_id = EXCLUDED.uploaded_video_id,
            uploaded_video_url = EXCLUDED.uploaded_video_url,
            upload_title = EXCLUDED.upload_title,
            local_file_path = EXCLUDED.local_file_path,
            error_message = EXCLUDED.error_message,
            download_attempts = EXCLUDED.download_attempts,
            upload_attempts = EXCLUDED.upload_attempts,
            updated_at = NOW()
        """
        params: dict[str, Any] = {
            "source_video_id": result.source_video_id,
            "source_video_url": source_url,
            "source_channel_label": source_channel_label,
            "target_channel_name": result.channel_name,
            "status": result.status,
            "uploaded_video_id": result.upload_video_id,
            "uploaded_video_url": uploaded_url,
            "upload_title": None,
            "local_file_path": result.local_file_path,
            "error_message": result.error_message,
            "download_attempts": result.download_attempts,
            "upload_attempts": result.upload_attempts,
        }
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
        self._logger.info(
            "Recorded %s result for source_video_id=%s target=%s",
            result.status,
            result.source_video_id,
            result.channel_name,
        )
