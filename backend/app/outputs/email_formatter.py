from __future__ import annotations


class EmailFormatter:
    """Format arbitrary response content into an email draft."""

    def format_as_email(
        self,
        content: str,
        subject_hint: str = "",
        to: str = "",
        from_name: str = "",
    ) -> dict[str, str]:
        subject = (subject_hint or self._extract_subject(content)).strip() or "Email Draft"
        body = self._clean_for_email(content)
        return {"to": to, "from": from_name, "subject": subject, "body": body}

    def _extract_subject(self, content: str) -> str:
        lines = (content or "").strip().splitlines()
        for line in lines:
            if line.lower().startswith("subject:"):
                return line.split(":", 1)[1].strip()
        first_line = lines[0] if lines else "Email Draft"
        return first_line[:80] + ("..." if len(first_line) > 80 else "")

    def _clean_for_email(self, content: str) -> str:
        lines = (content or "").strip().splitlines()
        cleaned = [line for line in lines if not line.lower().startswith("subject:")]
        return "\n".join(cleaned).strip()


email_formatter = EmailFormatter()

