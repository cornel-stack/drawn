"""Sources manifest handling: slug + sha256 pin rewrite (no network/PDF)."""

from drawn_schema import sources


def test_slug():
    assert sources._slug("11.4 Precession of a Gyroscope") == "11-4-precession-of-a-gyroscope"
    assert sources._slug("Kirchhoff's Rules!") == "kirchhoff-s-rules"


def test_load_manifest_reads_pins(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "manifest.yaml").write_text(
        "books:\n"
        "  - id: a\n    title: A\n    auto: true\n    url: http://x/a.pdf\n    sha256: abc\n"
        "  - id: b\n    title: B\n    auto: false\n    url: ''\n    sha256: ''\n"
    )
    books = sources.load_manifest(tmp_path)
    assert [b.id for b in books] == ["a", "b"]
    assert books[0].auto and books[0].sha256 == "abc"
    assert not books[1].auto


def test_write_pin_preserves_comments_and_targets_right_book(tmp_path):
    (tmp_path / "sources").mkdir()
    man = tmp_path / "sources" / "manifest.yaml"
    man.write_text(
        "# header comment\n"
        "books:\n"
        '  - id: a\n    title: A\n    sha256: ""\n'
        '  - id: b\n    title: B\n    sha256: ""\n'
    )
    sources._write_pin(tmp_path, "b", "deadbeef")
    text = man.read_text()
    assert "# header comment" in text
    # only book b's pin changed
    assert text.count('sha256: "deadbeef"') == 1
    reloaded = {bk.id: bk.sha256 for bk in sources.load_manifest(tmp_path)}
    assert reloaded == {"a": "", "b": "deadbeef"}
