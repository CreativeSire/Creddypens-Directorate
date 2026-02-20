from __future__ import annotations

import html

import markdown


class PDFGenerator:
    """Generate PDFs from markdown or plain text."""

    def __init__(self) -> None:
        self._css_string = """
        @page { size: A4; margin: 2cm; }
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #222; }
        h1, h2, h3 { color: #0891b2; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 6px; overflow: auto; }
        code { background: #f3f4f6; padding: 2px 6px; border-radius: 3px; }
        """

    def _build_renderer(self):
        try:
            from weasyprint import CSS, HTML  # type: ignore
        except Exception as exc:
            raise RuntimeError("PDF export requires WeasyPrint system dependencies") from exc
        return HTML, CSS(string=self._css_string)

    def generate_from_markdown(self, markdown_content: str, title: str = "Document") -> bytes:
        html_content = markdown.markdown(markdown_content or "", extensions=["tables", "fenced_code"])
        full_html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{html.escape(title)}</title></head><body>"
            f"<h1>{html.escape(title)}</h1>{html_content}</body></html>"
        )
        HTML, css = self._build_renderer()
        return HTML(string=full_html).write_pdf(stylesheets=[css])

    def generate_from_text(self, text: str, title: str = "Document") -> bytes:
        safe_text = html.escape(text or "").replace("\n", "<br>")
        full_html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{html.escape(title)}</title></head><body>"
            f"<h1>{html.escape(title)}</h1><div style='white-space: pre-wrap;'>{safe_text}</div>"
            "</body></html>"
        )
        HTML, css = self._build_renderer()
        return HTML(string=full_html).write_pdf(stylesheets=[css])


pdf_generator = PDFGenerator()
