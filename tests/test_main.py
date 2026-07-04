from __future__ import annotations

import os

import app.main as app_main


def test_sanitize_child_environment_removes_pm2_node_ipc_variable(monkeypatch) -> None:
    monkeypatch.setenv("NODE_CHANNEL_FD", "3")

    assert hasattr(app_main, "sanitize_child_process_environment")
    app_main.sanitize_child_process_environment()

    assert "NODE_CHANNEL_FD" not in os.environ

