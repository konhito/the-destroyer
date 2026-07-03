from pathlib import Path

from app.config import load_config


def test_load_config_reads_enabled_channel_pairs(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
database:
  dsn: postgresql://user:pass@localhost:5432/db
paths:
  downloads_dir: downloads
  failed_dir: failed
  logs_dir: logs
discovery:
  latest_only: true
channel_pairs:
  - name: test
    enabled: true
    source_url: https://www.youtube.com/@source/videos
    target_client_secret_json: creds.json
    target_oauth_token_json: token.json
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert len(config.enabled_channel_pairs()) == 1
    assert config.discovery.latest_only is True
    assert config.channel_pairs[0].target_oauth_token_json.name == "token.json"
