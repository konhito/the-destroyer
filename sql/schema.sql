CREATE TABLE IF NOT EXISTS processed_videos (
    id BIGSERIAL PRIMARY KEY,
    source_video_id TEXT NOT NULL,
    source_video_url TEXT NOT NULL,
    source_channel_label TEXT NOT NULL,
    target_channel_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
    uploaded_video_id TEXT,
    uploaded_video_url TEXT,
    upload_title TEXT,
    local_file_path TEXT,
    error_message TEXT,
    download_attempts INTEGER NOT NULL DEFAULT 0,
    upload_attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_video_id, target_channel_name)
);

CREATE INDEX IF NOT EXISTS idx_processed_videos_status
    ON processed_videos (status);

CREATE INDEX IF NOT EXISTS idx_processed_videos_target_channel
    ON processed_videos (target_channel_name);
