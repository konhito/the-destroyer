from __future__ import annotations

import argparse
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap OAuth token for one target YouTube channel.")
    parser.add_argument("--client-secret", required=True, help="Path to client secret JSON.")
    parser.add_argument("--token-out", required=True, help="Path to write authorized token JSON.")
    return parser


def create_token_from_flow(flow: InstalledAppFlow, token_out: Path) -> None:
    credentials = flow.run_local_server(port=0)
    token_out.parent.mkdir(parents=True, exist_ok=True)
    token_out.write_text(credentials.to_json(), encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    client_secret = Path(args.client_secret)
    token_out = Path(args.token_out)

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), YOUTUBE_SCOPES)
    create_token_from_flow(flow, token_out)
    print(f"Token written to {token_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
