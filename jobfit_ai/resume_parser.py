from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

from PyPDF2 import PdfReader
from jobfit_ai.limits import MAX_DOCX_XML_BYTES, MAX_PDF_PAGES, MAX_RESUME_CHARS

SUPPORTED_FILE_TYPES = {"pdf", "docx", "txt"}


class ResumeLimitError(ValueError):
    """A safe, user-facing extraction limit error."""


def _bounded_text(text: str) -> str:
    if len(text) > MAX_RESUME_CHARS:
        raise ResumeLimitError("Extracted resume text must be 100,000 characters or fewer.")
    return text.strip()


def extract_text_from_pdf(file_path: str | Path) -> str:
    reader = PdfReader(str(file_path))
    if len(reader.pages) > MAX_PDF_PAGES:
        raise ResumeLimitError("PDF resumes must contain 30 pages or fewer.")
    pages: list[str] = []
    char_count = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        char_count += len(text) + 1
        if char_count > MAX_RESUME_CHARS:
            raise ResumeLimitError("Extracted resume text must be 100,000 characters or fewer.")
        pages.append(text)
    return _bounded_text("\n".join(pages))


def extract_text_from_docx(file_path: str | Path) -> str:
    with ZipFile(file_path) as archive:
        if archive.getinfo("word/document.xml").file_size > MAX_DOCX_XML_BYTES:
            raise ResumeLimitError("DOCX document XML must be 2 MB or smaller when expanded.")
        with archive.open("word/document.xml") as member:
            xml_bytes = member.read(MAX_DOCX_XML_BYTES + 1)
        if len(xml_bytes) > MAX_DOCX_XML_BYTES:
            raise ResumeLimitError("DOCX document XML must be 2 MB or smaller when expanded.")
    root = ElementTree.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    word_namespace = "{" + namespace["w"] + "}"
    for paragraph in root.findall(".//w:p", namespace):
        chunks: list[str] = []
        # Traverse in document order: adjacent formatting runs can split a word,
        # while explicit Word tabs/breaks are real separators, not empty tags.
        for node in paragraph.iter():
            if node.tag == word_namespace + "t" and node.text:
                chunks.append(node.text)
            elif node.tag == word_namespace + "tab":
                chunks.append("\t")
            elif node.tag in {word_namespace + "br", word_namespace + "cr"}:
                chunks.append("\n")
        if chunks:
            paragraphs.append("".join(chunks))
    return _bounded_text("\n".join(paragraphs))


def extract_text_from_txt(file_path: str | Path) -> str:
    return _bounded_text(Path(file_path).read_text(encoding="utf-8-sig"))


def extract_resume_text(file_path: str | Path, source_type: str) -> str:
    normalized_type = source_type.lower()
    if normalized_type == "pdf":
        return extract_text_from_pdf(file_path)
    if normalized_type == "docx":
        return extract_text_from_docx(file_path)
    if normalized_type == "txt":
        return extract_text_from_txt(file_path)
    raise ValueError(f"Unsupported resume type: {source_type}")
