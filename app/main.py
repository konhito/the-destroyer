from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.config import load_config
from app.database import PostgresVideoRepository
from app.discovery import YtDlpDiscoveryClient
from app.downloader import YtDlpDownloader
from app.files import FileManager
from app.logging_utils import configure_logging
from app.runner import VideoAutomationRunner
from app.uploader import YouTubeUploadClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strictly sequential one-video-at-a-time YouTube automation runner."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML configuration file.",
    )
    return parser


def sanitize_child_process_environment() -> None:
    # PM2 exposes its Node IPC descriptor to managed processes. yt-dlp's
    # JavaScript runtimes inherit it and try to use an invalid IPC channel.
    os.environ.pop("NODE_CHANNEL_FD", None)


def main() -> int:
    sanitize_child_process_environment()
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    logger = configure_logging(config.paths.logs_dir)

    config.paths.downloads_dir.mkdir(parents=True, exist_ok=True)
    config.paths.failed_dir.mkdir(parents=True, exist_ok=True)

    runner = VideoAutomationRunner(
        config=config,
        repository=PostgresVideoRepository(config.database, logger),
        discovery=YtDlpDiscoveryClient(
            config.discovery,
            logger,
            cookies_file=config.ytdlp.cookies_file,
            js_runtime=config.ytdlp.js_runtime,
            remote_components=config.ytdlp.remote_components,
        ),
        downloader=YtDlpDownloader(
            config.paths.downloads_dir,
            logger,
            cookies_file=config.ytdlp.cookies_file,
            js_runtime=config.ytdlp.js_runtime,
            remote_components=config.ytdlp.remote_components,
        ),
        uploader=YouTubeUploadClient(config.upload_defaults, logger),
        file_manager=FileManager(config.paths.failed_dir),
        logger=logger,
    )
    processed_count = runner.run()
    logger.info("Run complete. processed_count=%s", processed_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
