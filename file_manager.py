"""UTF-8 TXT loading and atomic saving."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from PyQt5.QtCore import QIODevice, QSaveFile


@dataclass(frozen=True)
class TextFile:
    text: str
    newline: str = "\n"
    bom: bool = False
    source_digest: bytes | None = field(default=None, compare=False, repr=False)


def file_digest(path: str | Path) -> bytes:
    """Identify the exact bytes currently on disk before replacing a loaded file."""
    digest = sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def read_text_file(path: str | Path) -> TextFile:
    raw = Path(path).read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig" if bom else "utf-8")
    # QTextDocument uses LF internally. Retain the file's predominant line
    # ending separately so saving does not gratuitously rewrite every line.
    crlf = text.count("\r\n")
    lone_cr = text.count("\r") - crlf
    lone_lf = text.count("\n") - crlf
    newline = max(
        (("\r\n", crlf), ("\n", lone_lf), ("\r", lone_cr)),
        key=lambda item: item[1],
    )[0]
    return TextFile(
        text.replace("\r\n", "\n").replace("\r", "\n"),
        newline,
        bom,
        sha256(raw).digest(),
    )


def write_text_file(path: str | Path, document: TextFile) -> bytes:
    if document.newline not in ("\n", "\r\n", "\r"):
        raise ValueError("不支持的换行格式")
    content = document.text.replace("\n", document.newline).encode("utf-8")
    if document.bom:
        content = b"\xef\xbb\xbf" + content

    target = QSaveFile(str(path))
    if not target.open(QIODevice.WriteOnly):
        raise OSError(target.errorString())
    try:
        written = target.write(content)
        if written != len(content):
            raise OSError(target.errorString() or "写入内容不完整")
        if not target.commit():
            raise OSError(target.errorString())
        return sha256(content).digest()
    except Exception:
        target.cancelWriting()
        raise

