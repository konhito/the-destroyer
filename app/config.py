from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class DatabaseConfig:
    dsn: str


@dataclass(slots=True)
class RetryConfig:
    max_attempts: int = 6
    initial_delay_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 300.0


@dataclass(slots=True)
class DiscoveryConfig:
    latest_only: bool = True
    max_candidates: int = 10


@dataclass(slots=True)
class PathsConfig:
    downloads_dir: Path
    failed_dir: Path
    logs_dir: Path


@dataclass(slots=True)
class UploadDefaultsConfig:
    privacy_status: str = "private"
    category_id: str = "22"
    tags: list[str] = field(default_factory=list)
    title_prefix: str = ""
    description_prefix: str = ""
    description_suffix: str = ""
    chunk_size_bytes: int = 8 * 1024 * 1024


@dataclass(slots=True)
class ChannelPairConfig:
    name: str
    enabled: bool
    source_url: str
    source_channel_label: str
    target_channel_name: str
    target_client_secret_json: Path
    target_oauth_token_json: Path
    title_prefix: str = ""
    description_prefix: str = ""
    description_suffix: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppConfig:
    database: DatabaseConfig
    retry: RetryConfig
    discovery: DiscoveryConfig
    paths: PathsConfig
    upload_defaults: UploadDefaultsConfig
    channel_pairs: list[ChannelPairConfig]

    def enabled_channel_pairs(self) -> list[ChannelPairConfig]:
        return [pair for pair in self.channel_pairs if pair.enabled]


def _require(raw: dict[str, Any], key: str) -> Any:
    if key not in raw:
        raise ValueError(f"Missing required config key: {key}")
    return raw[key]


def _to_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def load_config(path: str | Path) -> AppConfig:
    config_path = _to_path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    database_raw = _require(raw, "database")
    retry_raw = raw.get("retry", {})
    discovery_raw = raw.get("discovery", {})
    paths_raw = _require(raw, "paths")
    upload_raw = raw.get("upload_defaults", {})
    channel_pairs_raw = _require(raw, "channel_pairs")

    config = AppConfig(
        database=DatabaseConfig(dsn=_require(database_raw, "dsn")),
        retry=RetryConfig(
            max_attempts=int(retry_raw.get("max_attempts", 6)),
            initial_delay_seconds=float(retry_raw.get("initial_delay_seconds", 5)),
            backoff_multiplier=float(retry_raw.get("backoff_multiplier", 2)),
            max_delay_seconds=float(retry_raw.get("max_delay_seconds", 300)),
        ),
        discovery=DiscoveryConfig(
            latest_only=bool(discovery_raw.get("latest_only", True)),
            max_candidates=int(discovery_raw.get("max_candidates", 10)),
        ),
        paths=PathsConfig(
            downloads_dir=_to_path(_require(paths_raw, "downloads_dir")),
            failed_dir=_to_path(_require(paths_raw, "failed_dir")),
            logs_dir=_to_path(_require(paths_raw, "logs_dir")),
        ),
        upload_defaults=UploadDefaultsConfig(
            privacy_status=str(upload_raw.get("privacy_status", "private")),
            category_id=str(upload_raw.get("category_id", "22")),
            tags=list(upload_raw.get("tags", [])),
            title_prefix=str(upload_raw.get("title_prefix", "")),
            description_prefix=str(upload_raw.get("description_prefix", "")),
            description_suffix=str(upload_raw.get("description_suffix", "")),
            chunk_size_bytes=int(upload_raw.get("chunk_size_bytes", 8 * 1024 * 1024)),
        ),
        channel_pairs=[
            ChannelPairConfig(
                name=str(_require(item, "name")),
                enabled=bool(item.get("enabled", False)),
                source_url=str(_require(item, "source_url")),
                source_channel_label=str(item.get("source_channel_label", item["name"])),
                target_channel_name=str(item.get("target_channel_name", item["name"])),
                target_client_secret_json=_to_path(_require(item, "target_client_secret_json")),
                target_oauth_token_json=_to_path(_require(item, "target_oauth_token_json")),
                title_prefix=str(item.get("title_prefix", "")),
                description_prefix=str(item.get("description_prefix", "")),
                description_suffix=str(item.get("description_suffix", "")),
                tags=list(item.get("tags", [])),
            )
            for item in channel_pairs_raw
        ],
    )

    return config
