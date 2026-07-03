# YouTube Sequential Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python 3.11 one-shot YouTube automation runner that processes one video at a time, uploads it to mapped target channels, records outcomes in NeonDB, and is deployable on EC2 with PM2 cron scheduling.

**Architecture:** Use a synchronous orchestrator with explicit dependency boundaries: config, retry, db, discovery, download, upload, file handling, and CLI entrypoint. Initial rollout processes one latest unprocessed video for one enabled channel pair, while the config format already supports scaling to five channel pairs without changing control flow.

**Tech Stack:** Python 3.11, PyYAML, yt-dlp, google-api-python-client, google-auth-oauthlib, psycopg 3, pytest, PM2

---

## File Structure

- `app/config.py` — YAML parsing into dataclasses
- `app/exceptions.py` — retriable and terminal exception types
- `app/models.py` — domain dataclasses
- `app/logging_utils.py` — console and rotating-file logger setup
- `app/retry.py` — exponential backoff helper
- `app/database.py` — PostgreSQL repository
- `app/discovery.py` — yt-dlp source discovery
- `app/downloader.py` — yt-dlp downloader
- `app/files.py` — delete/move helpers
- `app/uploader.py` — YouTube upload client
- `app/runner.py` — strict sequential orchestration
- `app/main.py` — CLI entrypoint
- `app/bootstrap_oauth.py` — one-time OAuth token bootstrap
- `tests/test_retry.py` — retry unit tests
- `tests/test_runner.py` — orchestration unit tests
- `tests/test_config.py` — config parsing tests
- `config.example.yaml` — sample configuration
- `sql/schema.sql` — NeonDB schema
- `ecosystem.config.js` — PM2 scheduler
- `README.md` — setup and deployment guide

### Task 1: Project skeleton and configuration

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/__main__.py`
- Create: `app/config.py`
- Create: `app/models.py`
- Create: `app/exceptions.py`
- Create: `config.example.yaml`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing config test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with import or missing function errors

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class ChannelPairConfig:
    name: str
    enabled: bool
    source_url: str
    target_client_secret_json: str
    target_oauth_token_json: str


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app tests config.example.yaml
git commit -m "feat: add project skeleton and config loader"
```

### Task 2: Retry and orchestration contracts

**Files:**
- Create: `app/retry.py`
- Create: `app/logging_utils.py`
- Create: `tests/test_retry.py`
- Create: `tests/test_runner.py`

- [ ] **Step 1: Write the failing retry and sequencing tests**

```python
from app.retry import RetryConfig, run_with_retry


def test_run_with_retry_retries_then_succeeds() -> None:
    attempts = {"count": 0}

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("retry me")
        return "ok"

    result = run_with_retry(flaky, RetryConfig(max_attempts=3))

    assert result.value == "ok"
    assert result.attempts == 3
```

```python
def test_runner_processes_one_video_in_order() -> None:
    calls = []
    ...
    assert calls == [
        "discover",
        "download",
        "upload",
        "record-success",
        "delete",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_retry.py tests/test_runner.py -v`
Expected: FAIL with missing modules and functions

- [ ] **Step 3: Write minimal implementation**

```python
def run_with_retry(operation, config, should_retry=None, sleep=time.sleep):
    ...
    return RetryOutcome(value=result, attempts=attempt)
```

```python
class VideoAutomationRunner:
    def run(self) -> int:
        for pair in self.config.enabled_channel_pairs():
            ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_retry.py tests/test_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app tests
git commit -m "feat: add retry utilities and sequential runner"
```

### Task 3: External integrations

**Files:**
- Create: `app/database.py`
- Create: `app/discovery.py`
- Create: `app/downloader.py`
- Create: `app/files.py`
- Create: `app/uploader.py`
- Create: `sql/schema.sql`

- [ ] **Step 1: Write a failing runner test for terminal failure handling**

```python
def test_runner_moves_failed_file_after_retries_exhausted() -> None:
    ...
    assert repo.records[0]["status"] == "failed"
    assert file_manager.moved == [downloaded_path]
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `python -m pytest tests/test_runner.py::test_runner_moves_failed_file_after_retries_exhausted -v`
Expected: FAIL because failure handling is not implemented yet

- [ ] **Step 3: Write minimal integration implementation**

```python
class PostgresVideoRepository:
    def upsert_video_record(...):
        with self.connection.cursor() as cur:
            cur.execute(...)
```

```python
class YtDlpDiscoveryClient:
    def list_videos(...):
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel.source_url, download=False)
```

```python
class YouTubeUploadClient:
    def upload(...):
        request = service.videos().insert(..., media_body=MediaFileUpload(...))
```

- [ ] **Step 4: Run the runner tests to verify they pass**

Run: `python -m pytest tests/test_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app sql tests
git commit -m "feat: add database and youtube integrations"
```

### Task 4: CLI, deployment, and docs

**Files:**
- Create: `app/main.py`
- Create: `app/bootstrap_oauth.py`
- Create: `ecosystem.config.js`
- Create: `README.md`

- [ ] **Step 1: Write a failing import smoke check**

```python
def test_app_entrypoint_imports() -> None:
    import app.main  # noqa: F401
```

- [ ] **Step 2: Run the full test suite to verify current gaps**

Run: `python -m pytest -v`
Expected: FAIL until CLI and docs-facing modules are in place

- [ ] **Step 3: Write minimal implementation**

```python
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    ...
    return 0
```

```javascript
module.exports = {
  apps: [
    {
      name: "youtube-sequential-automation",
      script: "python3.11",
      args: "-m app.main --config config.yaml",
      cron_restart: "0 2,10,18 * * *",
      autorestart: false,
    },
  ],
};
```

- [ ] **Step 4: Run full verification**

Run: `python -m pytest -v`
Expected: PASS

Run: `python -m app.main --help`
Expected: exit 0 and usage output

- [ ] **Step 5: Commit**

```bash
git add app README.md ecosystem.config.js
git commit -m "feat: add cli entrypoint and deployment docs"
```
