from dataclasses import dataclass
from pathlib import Path
import re

from docx import Document as DocxDocument
from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedPage:
    page_number: int | None
    text: str


@dataclass(frozen=True)
class ParsedChunk:
    chunk_index: int
    content: str
    char_count: int
    page_start: int | None
    page_end: int | None


def parse_document_pages(path: str) -> list[ParsedPage]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(file_path)
    if suffix in {".txt", ".md"}:
        return [ParsedPage(page_number=None, text=file_path.read_text(encoding="utf-8"))]
    if suffix == ".docx":
        return _parse_docx(file_path)

    raise ValueError(f"Unsupported parser type: {suffix or 'unknown'}")


def build_chunks(
    pages: list[ParsedPage],
    chunk_size: int = 900,
    chunk_overlap: int = 120,
) -> list[ParsedChunk]:
    chunks: list[ParsedChunk] = []
    for page in pages:
        text = _normalize_text(page.text)
        if not text:
            continue

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            content = text[start:end].strip()
            if content:
                chunks.append(
                    ParsedChunk(
                        chunk_index=len(chunks),
                        content=content,
                        char_count=len(content),
                        page_start=page.page_number,
                        page_end=page.page_number,
                    )
                )
            if end == len(text):
                break
            start = max(end - chunk_overlap, start + 1)

    if not chunks:
        raise ValueError("No readable text was extracted from this document.")

    return chunks


def _parse_pdf(path: Path) -> list[ParsedPage]:
    reader = PdfReader(str(path))
    pages: list[ParsedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append(ParsedPage(page_number=index, text=page.extract_text() or ""))
    return pages


def _parse_docx(path: Path) -> list[ParsedPage]:
    document = DocxDocument(str(path))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    return [ParsedPage(page_number=None, text=text)]


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
