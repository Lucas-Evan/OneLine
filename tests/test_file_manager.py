from __future__ import annotations

from file_manager import TextFile, read_text_file, write_text_file


def test_open_utf8_txt_and_bom(tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_bytes("中文第一行\n第二行".encode("utf-8"))
    with_bom = tmp_path / "bom.txt"
    with_bom.write_bytes(b"\xef\xbb\xbf" + "带 BOM\r\n第二行".encode("utf-8"))

    assert read_text_file(plain) == TextFile("中文第一行\n第二行")
    assert read_text_file(with_bom) == TextFile("带 BOM\n第二行", "\r\n", True)


def test_atomic_save_preserves_bom_and_newlines(tmp_path):
    path = tmp_path / "document.txt"
    document = TextFile("第一行\n第二行\n第三行", "\r\n", True)
    write_text_file(path, document)

    assert path.read_bytes() == b"\xef\xbb\xbf" + document.text.replace(
        "\n", "\r\n"
    ).encode("utf-8")
    assert read_text_file(path) == document


def test_long_multiline_save_round_trip(tmp_path):
    path = tmp_path / "long.txt"
    text = "很长的中文内容" * 2000 + "\n" + "\n".join(
        f"第 {number} 行" for number in range(100)
    )
    write_text_file(path, TextFile(text))

    assert read_text_file(path).text == text
