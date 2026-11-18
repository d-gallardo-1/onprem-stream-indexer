"""Cell helpers shared by the sheets of the export workbook."""

from __future__ import annotations

from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

SYNTHETIC_NOTE = "Synthetic demo data. No real ruling, authority, statute or person."

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="1F2937")
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def safe_cell(value: object) -> object:
    """Stop a spreadsheet program from running text as a formula.

    Titles and summaries are text. A text cell that starts with a formula
    character is prefixed with an apostrophe, so it is shown, not evaluated.
    Numbers are passed through untouched.
    """
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def write_header(sheet: Worksheet, row: int, columns: tuple[str, ...] | list[str]) -> None:
    for position, name in enumerate(columns, start=1):
        cell = sheet.cell(row=row, column=position, value=name)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        sheet.column_dimensions[cell.column_letter].width = max(16, min(48, len(name) + 8))


def append_row(sheet: Worksheet, values: list[object]) -> None:
    sheet.append([safe_cell(value) for value in values])
