from app.uploader import _close_media_upload


class FakeFile:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeMediaUpload:
    def __init__(self) -> None:
        self._fd = FakeFile()


def test_close_media_upload_closes_open_file_handle() -> None:
    media = FakeMediaUpload()

    _close_media_upload(media)

    assert media._fd.closed is True
