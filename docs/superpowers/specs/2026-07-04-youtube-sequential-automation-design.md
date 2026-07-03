# YouTube Sequential Automation Design

## Goal

Build a production-ready Python automation system that discovers videos from source YouTube channels, downloads exactly one video at a time, uploads it to a mapped target YouTube channel, records the result in NeonDB, and exits cleanly. The initial rollout will enable one channel pair and process only the latest unprocessed video per run. The design must scale to five channel pairs without changing the execution model.

## Scope

- Python 3.11+ CLI job
- Strictly sequential execution
- yt-dlp source discovery and downloading
- YouTube Data API v3 resumable uploads
- NeonDB/PostgreSQL tracking
- PM2 cron-based scheduling on EC2
- One active channel pair for initial testing, up to five supported by config

## Runtime Architecture

The system is a one-shot CLI runner. A single process loads configuration, connects to PostgreSQL, loops through enabled channel pairs in config order, discovers candidate source videos, filters already-successful uploads, and processes at most one candidate per pair for the initial phase. Each video follows a hard sequence:

1. Discover candidate
2. Download video locally
3. Upload the downloaded file
4. Record result in PostgreSQL
5. Delete the local file on success or move it to `failed/` on final failure

The codebase uses focused modules: configuration loading, logging, retry logic, data persistence, discovery, downloading, uploading, and orchestration. No threads, async fan-out, multiprocessing, or worker pool are used.

## Strict Sequencing Guarantee

The runner never begins a second video while the current video is unresolved. A video is unresolved until one of these terminal states occurs:

- Success: upload completed, success row committed to PostgreSQL, local file deleted
- Final failure: retries exhausted or non-retriable error raised, failure row committed, file moved to `failed/` if present

This guarantee is enforced structurally by a plain synchronous `for` loop over channel pairs and a plain synchronous `for` loop over videos, with processing encapsulated in a single `process_video` function.

## Discovery Model

Source discovery uses yt-dlp metadata extraction from each source uploads URL. The configuration should point to the source channel uploads feed or equivalent page that yt-dlp can enumerate reliably. Discovery fetches a bounded set of recent entries and converts them into normalized candidate objects. The runner filters out videos already recorded as successful for that target channel.

Initial rollout behavior:

- `latest_only: true`
- one enabled channel pair
- one latest unprocessed video processed per run

Scale-up behavior:

- enable more channel pairs
- optionally switch `latest_only` to `false`
- still keep the same strict one-video-at-a-time sequence

## Download Model

Downloads use yt-dlp with a deterministic output template rooted in the configured downloads directory. Each download is retried with exponential backoff for transient failures. Non-retriable conditions such as private, deleted, or unavailable videos are detected and short-circuited.

## Upload Model

Uploads use the YouTube Data API v3 with resumable chunked uploads through `google-api-python-client`. Each target channel has its own OAuth client secret JSON and token JSON path. On first setup, a helper bootstrap command generates the token file for each target channel. Upload metadata combines:

- channel-level title prefix
- original source title
- channel-level description prefix/suffix
- global tags plus channel tags
- category id
- privacy status

Upload retries use exponential backoff for retriable API and network failures, including selected rate-limit and 5xx cases.

## Data Model

NeonDB uses one primary tracking table:

- `processed_videos`

The unique identity is `(source_video_id, target_channel_name)`. Rows are upserted on success or failure, so a later successful retry can overwrite an earlier failed status. The runner only skips rows with `status = 'success'`, preserving failed rows as audit history without permanently blocking later retries.

Stored data includes:

- source video id and URL
- source channel name/url
- target channel name
- status
- uploaded YouTube video id
- local file path
- title used for upload
- attempt counts
- error details
- created/updated timestamps

## File and Logging Model

Configured directories:

- `downloads/` for active downloads
- `failed/` for terminal failures
- `logs/` for rotating log files
- `tokens/` for per-channel OAuth tokens

Logging writes both to stdout and to a rotating log file with timestamps, level, module, and message text containing video ids and channel names.

## Error Handling

The system distinguishes:

- retriable errors: network interruptions, selected yt-dlp transient failures, selected YouTube API transient/rate-limit responses
- non-retriable errors: private/deleted/unavailable source videos, invalid configuration, unsupported credential files

Retry policy is configurable and defaults to six attempts with exponential backoff and an upper sleep bound.

## Deployment Model

PM2 runs the Python module as a one-shot process. PM2 handles scheduling with `cron_restart` three times per day. `autorestart` stays disabled so a normal successful exit does not create a loop. Logs are preserved both by PM2 and the application log files.

## Verification Strategy

Core verification covers:

- config parsing
- retry behavior
- strict sequential orchestration order
- failure handling and failed-file movement

The project includes pytest tests for orchestration and retry logic plus startup validation via CLI import and config load instructions in the README.
