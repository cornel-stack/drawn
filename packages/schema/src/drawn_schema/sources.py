"""Open-textbook sources: download, integrity-pin, per-section text extraction.

``just sources`` reads ``sources/manifest.yaml`` and, for each book with
``auto: true``:

1. downloads ``url`` to ``sources/<id>.pdf`` (gitignored) if missing;
2. verifies the file's sha256 against the manifest pin — or, when the pin is
   empty, records the computed hash back into the manifest so the next commit
   locks it;
3. extracts text per section from the PDF outline into
   ``sources/text/<id>/<NN-slug>.md``, each with a front line recording the
   source book, section title and PDF page range.

Lessons cite a section via ``source.file`` (the extracted ``.md``) and
``source.pages`` (the PDF page range), which the fact-check gate resolves.

PDFs and extracted text are gitignored; only the manifest (with its pins) is
committed. CI runs ``just sources`` too and caches the PDFs by sha256, so the
download happens at most once per hash.
"""

from __future__ import annotations

import hashlib
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Book:
    id: str
    title: str
    publisher: str
    licence: str
    auto: bool
    url: str
    sha256: str


def manifest_path(repo_root: Path) -> Path:
    return Path(repo_root) / "sources" / "manifest.yaml"


def pdf_path(repo_root: Path, book_id: str) -> Path:
    return Path(repo_root) / "sources" / f"{book_id}.pdf"


def text_dir(repo_root: Path, book_id: str) -> Path:
    return Path(repo_root) / "sources" / "text" / book_id


def load_manifest(repo_root: Path) -> list[Book]:
    data = yaml.safe_load(manifest_path(repo_root).read_text())
    return [
        Book(
            id=b["id"],
            title=b["title"],
            publisher=b.get("publisher", ""),
            licence=b.get("licence", ""),
            auto=bool(b.get("auto", False)),
            url=b.get("url", "") or "",
            sha256=b.get("sha256", "") or "",
        )
        for b in data.get("books", [])
    ]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_pin(repo_root: Path, book_id: str, digest: str) -> None:
    """Record a computed sha256 into the manifest, preserving comments/layout.

    Finds the ``sha256:`` line that follows the matching ``id:`` line and
    rewrites just that line, so the hand-written header and ordering survive.
    """
    path = manifest_path(repo_root)
    lines = path.read_text().splitlines()
    in_book = False
    for i, line in enumerate(lines):
        if re.match(rf"\s*-?\s*id:\s*{re.escape(book_id)}\s*$", line):
            in_book = True
        elif re.match(r"\s*-\s*id:\s*", line):
            in_book = False
        if in_book and re.match(r"\s*sha256:\s*", line):
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = f'{indent}sha256: "{digest}"'
            break
    path.write_text("\n".join(lines) + "\n")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "drawn/0.1 (+sources)"})
    with urllib.request.urlopen(req) as resp, tmp.open("wb") as out:  # noqa: S310
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    tmp.replace(dest)


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")[:80]


def ensure_pdf(repo_root: Path, book: Book) -> Path:
    """Download the book if missing and verify/record its sha256."""
    dest = pdf_path(repo_root, book.id)
    if not dest.is_file():
        if not book.url:
            raise ValueError(f"{book.id}: no url to download")
        print(f"  downloading {book.id} …")
        _download(book.url, dest)
    digest = _sha256(dest)
    if book.sha256:
        if digest != book.sha256:
            dest.unlink(missing_ok=True)
            raise ValueError(
                f"{book.id}: sha256 mismatch\n  manifest {book.sha256}\n  file     {digest}"
            )
    else:
        print(f"  {book.id}: recording sha256 {digest}")
        _write_pin(repo_root, book.id, digest)
        book.sha256 = digest
    return dest


def _toc_sections(doc) -> list[tuple[str, int, int]]:
    """From a PDF outline, yield (title, first_page, last_page) 1-based.

    Uses the deepest outline level present so chapters split into their numbered
    sections; falls back to one entry per top-level chapter when there are no
    sub-sections.
    """
    toc = doc.get_toc(simple=True)  # [[level, title, page], ...], page 1-based
    if not toc:
        return []
    deepest = max(level for level, _t, _p in toc)
    # use level 2 (sections) when available, else whatever the deepest is
    want = 2 if deepest >= 2 else deepest
    marks = [(t, p) for level, t, p in toc if level == want and p >= 1]
    n_pages = doc.page_count
    out: list[tuple[str, int, int]] = []
    for i, (title, page) in enumerate(marks):
        end = (marks[i + 1][1] - 1) if i + 1 < len(marks) else n_pages
        out.append((title, page, max(page, end)))
    return out


def extract_sections(repo_root: Path, book: Book) -> int:
    """Extract per-section text into sources/text/<id>/. Returns section count."""
    import pymupdf as fitz  # lazy — only the sources step needs it

    pdf = pdf_path(repo_root, book.id)
    doc = fitz.open(str(pdf))
    out_dir = text_dir(repo_root, book.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    sections = _toc_sections(doc)
    seen: dict[str, int] = {}
    count = 0
    for idx, (title, first, last) in enumerate(sections, start=1):
        slug = _slug(title) or f"section-{idx}"
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        body = "\n".join(
            doc.load_page(p - 1).get_text("text") for p in range(first, last + 1)
        )
        header = (
            f"<!-- {book.title} ({book.publisher}, {book.licence}) "
            f"— {title} — PDF pages {first}-{last} -->\n\n"
        )
        (out_dir / f"{idx:03d}-{slug}.md").write_text(header + body)
        count += 1
    doc.close()
    return count


def run_sources(repo_root: Path, *, only: str | None = None) -> int:
    """Download + extract every auto book (or just ``only``). Returns 0 on ok."""
    books = load_manifest(Path(repo_root))
    todo = [b for b in books if b.auto and (only is None or b.id == only)]
    if not todo:
        print("no auto-downloadable books selected" + (f" matching {only!r}" if only else ""))
        return 0 if only is None else 1
    for book in todo:
        print(f"{book.id}: {book.title}")
        ensure_pdf(Path(repo_root), book)
        n = extract_sections(Path(repo_root), book)
        print(f"  extracted {n} sections -> sources/text/{book.id}/")
    return 0
