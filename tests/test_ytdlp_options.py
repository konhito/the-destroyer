from __future__ import annotations

import logging
from pathlib import Path

from app.config import ChannelPairConfig, DiscoveryConfig
from app.discovery import YtDlpDiscoveryClient
from app.downloader import YtDlpDownloader
from app.models import VideoCandidate


class RecordingYoutubeDL:
    last_opts: dict | None = None

    def __init__(self, opts: dict) -> None:
        RecordingYoutubeDL.last_opts = opts

    def __enter__(self) -> "RecordingYoutubeDL":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def extract_info(self, url: str, download: bool = False) -> dict:
        if download:
            return {"id": "abc123", "ext": "mp4", "requested_downloads": [{"filepath": "video.mp4"}]}
        return {"entries": [{"id": "abc123", "title": "Example", "url": "https://www.youtube.com/watch?v=abc123"}]}

    def prepare_filename(self, metadata: dict) -> str:
        return "video.mp4"


def test_discovery_passes_cookie_and_js_options(monkeypatch) -> None:
    monkeypatch.setattr("app.discovery.YoutubeDL", RecordingYoutubeDL)
    client = YtDlpDiscoveryClient(
        DiscoveryConfig(latest_only=True, max_candidates=10),
        logging.getLogger("test-discovery-options"),
        cookies_file=Path("cookies.txt"),
        js_runtime="node",
        remote_components="ejs:github",
    )

    channel = ChannelPairConfig(
        name="pair-01",
        enabled=True,
        source_url="https://www.youtube.com/@source/shorts",
        source_channel_label="Source",
        target_channel_name="Target",
        target_client_secret_json=Path("client.json"),
        target_oauth_token_json=Path("token.json"),
    )

    client.list_videos(channel)

    assert RecordingYoutubeDL.last_opts is not None
    assert RecordingYoutubeDL.last_opts["cookiefile"] == "cookies.txt"
    assert RecordingYoutubeDL.last_opts["js_runtimes"] == {"node": None}
    assert RecordingYoutubeDL.last_opts["remote_components"] == "ejs:github"


def test_downloader_passes_cookie_and_js_options(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.downloader.YoutubeDL", RecordingYoutubeDL)
    downloader = YtDlpDownloader(
        tmp_path / "downloads",
        logging.getLogger("test-downloader-options"),
        cookies_file=Path("cookies.txt"),
        js_runtime="node",
        remote_components="ejs:github",
    )

    channel = ChannelPairConfig(
        name="pair-01",
        enabled=True,
        source_url="https://www.youtube.com/@source/shorts",
        source_channel_label="Source",
        target_channel_name="Target",
        target_client_secret_json=Path("client.json"),
        target_oauth_token_json=Path("token.json"),
    )
    video = VideoCandidate(
        video_id="abc123",
        title="Example",
        webpage_url="https://www.youtube.com/watch?v=abc123",
    )

    downloader.download(channel, video)

    assert RecordingYoutubeDL.last_opts is not None
    assert RecordingYoutubeDL.last_opts["cookiefile"] == "cookies.txt"
    assert RecordingYoutubeDL.last_opts["js_runtimes"] == {"node": None}
    assert RecordingYoutubeDL.last_opts["remote_components"] == "ejs:github"
