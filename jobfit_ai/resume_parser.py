from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

from PyPDF2 import PdfReader

SUPPORTED_FILE_TYPES = {"pdf", "docx", "txt"}


def extract_text_from_pdf(file_path: str | Path) -> str:
    reader = PdfReader(str(file_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def extract_text_from_docx(file_path: str | Path) -> str:
    with ZipFile(file_path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        chunks = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
        if chunks:
            paragraphs.append("".join(chunks))
    return "\n".join(paragraphs).strip()


def extract_text_from_txt(file_path: str | Path) -> str:
    return Path(file_path).read_text(encoding="utf-8").strip()


def extract_resume_text(file_path: str | Path, source_type: str) -> str:
    normalized_type = source_type.lower()
    if normalized_type == "pdf":
        return extract_text_from_pdf(file_path)
    if normalized_type == "docx":
        return extract_text_from_docx(file_path)
    if normalized_type == "txt":
        return extract_text_from_txt(file_path)
    raise ValueError(f"Unsupported resume type: {source_type}")
