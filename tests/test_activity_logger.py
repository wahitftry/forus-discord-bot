from types import SimpleNamespace

import pytest

from bot.services.activity_logger import format_attachments, format_user, truncate_content


class DummyAttachment:
    def __init__(self, filename: str, url: str | None = None) -> None:
        self.filename = filename
        self.url = url


@pytest.mark.parametrize(
    "text,limit,expected",
    [
        ("halo dunia", 20, "halo dunia"),
        (" " * 3 + "panjang" + "x" * 1100, 20, "panjang" + "x" * 12 + "…"),
        ("", 10, ""),
    ],
)
def test_truncate_content(text: str, limit: int, expected: str) -> None:
    assert truncate_content(text, limit=limit) == expected


def test_format_attachments_with_links() -> None:
    attachments = [
        DummyAttachment("a.png", "https://cdn/a.png"),
        DummyAttachment("b.jpg", "https://cdn/b.jpg"),
        DummyAttachment("c.gif", "https://cdn/c.gif"),
        DummyAttachment("d.mov", "https://cdn/d.mov"),
        DummyAttachment("e.txt", "https://cdn/e.txt"),
        DummyAttachment("f.zip", "https://cdn/f.zip"),
    ]
    result = format_attachments(attachments)
    assert result is not None
    lines = result.split("\n")
    assert len(lines) == 6
    assert lines[0] == "[a.png](https://cdn/a.png)"
    assert lines[-1] == "+1 lampiran lainnya"


def test_format_attachments_without_links() -> None:
    attachments = [DummyAttachment("cat.png", None)]
    assert format_attachments(attachments) == "cat.png"


def test_format_user_defaults() -> None:
    dummy = SimpleNamespace(mention="@user", id=123456, display_name="Dummy")
    assert format_user(dummy) == "@user (`123456`)"
    assert format_user(None) == "Unknown"
