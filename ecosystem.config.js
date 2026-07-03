module.exports = {
  apps: [
    {
      name: "youtube-sequential-automation",
      cwd: __dirname,
      script: "python3.11",
      args: "-m app.main --config config.yaml",
      interpreter: "none",
      autorestart: false,
      watch: false,
      cron_restart: "0 2,10,18 * * *",
      time: true,
      env: {
        PYTHONUNBUFFERED: "1",
      },
      out_file: "./logs/pm2-out.log",
      error_file: "./logs/pm2-error.log",
      merge_logs: true,
    },
  ],
};
