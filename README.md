# YouTube Sequential Automation

Strictly sequential YouTube automation in Python. The runner processes one video at a time:

1. discover a source video
2. download that video
3. upload it to the mapped target channel
4. record the result in NeonDB
5. delete the local file on success or move it to `failed/` on final failure

The next video never starts until the current one reaches a terminal state.

## Current rollout

- Initial source channel is hardcoded in the shipped `config.yaml`:
  - `https://www.youtube.com/@dafsdgfsd/shorts`
- Only `pair-01` is enabled by default
- `discovery.latest_only: true` means one latest unprocessed video per run
- The code already supports up to five channel pairs by config

## Project structure

```text
app/
  bootstrap_oauth.py
  config.py
  database.py
  discovery.py
  downloader.py
  exceptions.py
  files.py
  logging_utils.py
  main.py
  models.py
  retry.py
  runner.py
config.yaml
config.example.yaml
docs/superpowers/
ecosystem.config.js
sql/schema.sql
tests/
```

## Requirements

- Python 3.11+
- Node.js + PM2
- ffmpeg
- Google Cloud OAuth desktop credentials for each target YouTube channel
- NeonDB PostgreSQL database

## Install locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## Configuration

Edit `config.yaml`.

Important fields:

- `database.dsn` — NeonDB connection string
- `discovery.latest_only` — keep `true` for initial rollout
- `ytdlp.cookies_file` — Netscape-format YouTube cookies file
- `ytdlp.js_runtime` — set to `node`
- `ytdlp.remote_components` — set to `ejs:github`
- `channel_pairs[].enabled` — enable only the pairs you want active
- `channel_pairs[].source_url` — current initial value is `https://www.youtube.com/@dafsdgfsd/shorts`
- `channel_pairs[].target_client_secret_json` — Google OAuth client secret path
- `channel_pairs[].target_oauth_token_json` — authorized token path for that target channel

## NeonDB setup

Create a Neon project and run:

```sql
\i sql/schema.sql
```

Or paste the contents of [sql/schema.sql](sql/schema.sql) into the Neon SQL editor.

## Google OAuth setup

You need one OAuth desktop client JSON per target YouTube channel.

Steps:

1. Open Google Cloud Console
2. Create or select a project
3. Enable the YouTube Data API v3
4. Configure OAuth consent screen
5. Create Desktop App OAuth credentials
6. Download the JSON file
7. Put it in `./credentials/`

Bootstrap the token for each enabled target channel:

```bash
python -m app.bootstrap_oauth \
  --client-secret ./credentials/pair-01-client-secret.json \
  --token-out ./tokens/pair-01-token.json
```

That command opens a console-based OAuth flow and writes the refreshable token JSON.

## Run manually

```bash
python -m app.main --config config.yaml
```

The script runs once and exits.

## PM2 deployment on AWS EC2

Example target: Ubuntu 22.04 or Amazon Linux 2023.

### 1. Install system packages

Ubuntu:

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip ffmpeg curl git
```

Amazon Linux 2023:

```bash
sudo dnf install -y python3.11 python3.11-pip ffmpeg git
```

### 2. Install Node.js and PM2

```bash
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs
sudo npm install -g pm2
```

For Ubuntu:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

### 3. Upload the project

Clone or copy this project to the EC2 host, for example:

```bash
mkdir -p ~/youtube-sequential-automation
cd ~/youtube-sequential-automation
```

### 4. Create Python environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

### 5. Configure files

- edit `config.yaml`
- set your NeonDB DSN
- place a valid Netscape-format YouTube cookie file at `cookies.txt`
- place OAuth client JSON files in `credentials/`
- generate token JSON files in `tokens/`

### 5a. yt-dlp YouTube challenge prerequisites

The downloader currently expects:

- `yt-dlp[default]`
- Node.js
- `remote_components: ejs:github`
- a valid YouTube `cookies.txt`

Manual raw yt-dlp check:

```bash
python -m yt_dlp --js-runtimes node --remote-components ejs:github --cookies ./cookies.txt "https://www.youtube.com/watch?v=Up12A2K4EIQ"
```

### 6. Apply database schema

Run the SQL in `sql/schema.sql` against NeonDB.

### 7. Manual smoke test

```bash
source .venv/bin/activate
python -m app.main --config config.yaml
```

Check:

- console logs
- `logs/automation.log`
- rows in NeonDB
- uploaded video on the target channel
- `failed/` if any terminal failure occurred

### 8. Start with PM2

If `python3.11` is not on PATH, edit `ecosystem.config.js` and replace `script` with the absolute interpreter path, for example:

```javascript
script: "/home/ec2-user/youtube-sequential-automation/.venv/bin/python",
args: "-m app.main --config config.yaml",
```

Start:

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

The included schedule is:

```cron
0 2,10,18 * * *
```

Change it if you want different three-times-per-day slots.

### 9. PM2 monitoring

```bash
pm2 status
pm2 logs youtube-sequential-automation
pm2 describe youtube-sequential-automation
pm2 restart youtube-sequential-automation
pm2 stop youtube-sequential-automation
pm2 delete youtube-sequential-automation
```

## Failure behavior

- Download and upload each retry up to the configured limit
- Exponential backoff between retries
- Private/deleted/unavailable videos are treated as terminal failures
- On final failure, the file is moved to `failed/` if it exists
- Failure is recorded in NeonDB
- Successful uploads are recorded in NeonDB and the local file is deleted

## Scaling from one pair to five

When the first pair is stable:

1. create OAuth client/token files for the next target channel
2. set `enabled: true` on the next pair in `config.yaml`
3. optionally switch `discovery.latest_only` to `false`

The runtime remains strictly sequential. More pairs do not introduce parallelism.

## Verification

Run:

```bash
python -m pytest -v
python -m app.main --help
```

## Notes

- For best yt-dlp discovery results, keep `source_url` pointed at a channel uploads/shorts page that yt-dlp can enumerate reliably.
- If you need a stronger audit trail later, you can extend the database model with a separate run-history table without changing the strict execution model.
