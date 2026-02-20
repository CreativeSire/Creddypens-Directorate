from __future__ import annotations

import base64
import csv
from io import BytesIO, StringIO
from pathlib import Path

from PIL import Image
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text.strip())
    return "\n\n".join(chunks).strip()


def extract_docx(path: Path) -> str:
    document = Document(str(path))
    chunks = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(chunks).strip()


def _dataframe_to_text(dataframe: pd.DataFrame, max_rows: int = 50) -> str:
    trimmed = dataframe.head(max_rows)
    if trimmed.empty:
        return ""
    buffer = StringIO()
    trimmed.to_csv(buffer, index=False)
    return buffer.getvalue().strip()


def extract_excel(path: Path) -> str:
    dataframe = pd.read_excel(path)
    return _dataframe_to_text(dataframe)


def extract_csv(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        sample = handle.read(4 * 1024)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        reader = csv.reader(handle, dialect)
        rows = list(reader)[:50]
    if not rows:
        return ""
    return "\n".join(",".join(cell for cell in row) for row in rows)


def extract_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def encode_image_base64(path: Path) -> str:
    with Image.open(path) as image:
        image.thumbnail((1024, 1024))
        buffer = BytesIO()
        image.save(buffer, format=image.format or "PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/{(path.suffix or '.png').replace('.', '')};base64,{encoded}"


def extract_file_content(path: Path, mime_type: str, filename: str) -> str:
    lower_name = filename.lower()
    mime = (mime_type or "").lower()
    if lower_name.endswith(".pdf") or "pdf" in mime:
        return extract_pdf(path)
    if lower_name.endswith(".docx") or "word" in mime:
        return extract_docx(path)
    if lower_name.endswith(".xlsx") or "sheet" in mime:
        return extract_excel(path)
    if lower_name.endswith(".csv") or "csv" in mime:
        return extract_csv(path)
    if lower_name.endswith((".txt", ".md", ".json")) or mime.startswith("text/"):
        return extract_text_file(path)
    if lower_name.endswith((".png", ".jpg", ".jpeg", ".webp")) or mime.startswith("image/"):
        return encode_image_base64(path)
    return ""
