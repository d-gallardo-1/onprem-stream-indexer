"""Cell helpers shared by the sheets of the export workbook."""

from __future__ import annotations

from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

SYNTHETIC_NOTE = "Synthetic demo data. No real ruling, authority, statute or person."

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="1F2937")
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def safe_cell(value: object) -> object:
    """Make text safe to store in a cell and stop it from running as a formula.

    Control characters that a workbook cannot hold are dropped; without this a
    query such as a single U+0001 would make the export fail. Text whose first
    visible character is a formula character is then prefixed with an
    apostrophe, so it is shown, not evaluated; leading spaces, tabs and
    carriage returns do not hide it. Numbers are passed through untouched.
    """
    if not isinstance(value, str):
        return value
    text = ILLEGAL_CHARACTERS_RE.sub("", value)
    if text.lstrip().startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def write_header(sheet: Worksheet, row: int, columns: tuple[str, ...] | list[str]) -> None:
    for position, name in enumerate(columns, start=1):
        cell = sheet.cell(row=row, column=position, value=name)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        sheet.column_dimensions[cell.column_letter].width = max(16, min(48, len(name) + 8))


def append_row(sheet: Worksheet, values: list[object]) -> None:
    sheet.append([safe_cell(value) for value in values])
