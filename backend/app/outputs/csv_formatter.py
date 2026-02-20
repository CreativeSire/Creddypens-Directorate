from __future__ import annotations

import csv
import io
from typing import Any


class CSVFormatter:
    """Format structured or table-like text into CSV."""

    def format_dict_list(self, data: list[dict[str, Any]], columns: list[str] | None = None) -> str:
        if not data:
            return ""
        if not columns:
            columns = list(data[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def parse_table_from_text(self, text: str) -> str:
        lines = [line for line in (text or "").strip().splitlines() if line.strip()]
        table_lines = [line for line in lines if "|" in line]
        if not table_lines:
            return ""

        rows: list[list[str]] = []
        for line in table_lines:
            trimmed = line.strip()
            if all(ch in "|-: " for ch in trimmed):
                continue
            cells = [cell.strip() for cell in trimmed.split("|") if cell.strip()]
            if cells:
                rows.append(cells)
        if not rows:
            return ""

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(rows)
        return output.getvalue()


csv_formatter = CSVFormatter()

