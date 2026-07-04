from app.uploader import _close_media_upload, _is_retriable_upload_error


class FakeFile:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeMediaUpload:
    def __init__(self) -> None:
        self._fd = FakeFile()


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


class FakeHttpError:
    def __init__(self, status: int, content: bytes) -> None:
        self.resp = FakeResponse(status)
        self.content = content

    def __str__(self) -> str:
        return "fake-http-error"


def test_close_media_upload_closes_open_file_handle() -> None:
    media = FakeMediaUpload()

    _close_media_upload(media)

    assert media._fd.closed is True


def test_is_retriable_upload_error_handles_none_reason_entries() -> None:
    exc = FakeHttpError(
        403,
        b'{"error":{"errors":[null,{"reason":"quotaExceeded"}]}}',
    )

    assert _is_retriable_upload_error(exc) is True
