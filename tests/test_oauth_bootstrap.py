from pathlib import Path

from app.bootstrap_oauth import create_token_from_flow


class FakeCredentials:
    def to_json(self) -> str:
        return '{"token":"abc"}'


class FakeFlow:
    def __init__(self) -> None:
        self.called = False

    def run_local_server(self, port: int = 0) -> FakeCredentials:
        self.called = True
        return FakeCredentials()


def test_create_token_from_flow_uses_local_server(tmp_path: Path) -> None:
    token_out = tmp_path / "token.json"
    flow = FakeFlow()

    create_token_from_flow(flow, token_out)

    assert flow.called is True
    assert token_out.read_text(encoding="utf-8") == '{"token":"abc"}'
