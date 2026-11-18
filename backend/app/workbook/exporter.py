"""Writes the report workbook of one tenant query."""

from __future__ import annotations

import io

from openpyxl import Workbook

from ..analytics.models import Analytics
from ..models import Ruling, Tenant
from .layout import SYNTHETIC_NOTE, append_row, safe_cell, write_header

RESULT_COLUMNS: tuple[str, ...] = (
    "Docket ID", "Title", "Authority", "Matter", "Decision date", "Outcome",
    "Financial exposure (GBP)", "Cited articles", "Judge or inspector", "Summary excerpt",
)
#: Row of the column header on the Results sheet (title, note and a blank row above it).
HEADER_ROW = 4


def _results_sheet(workbook: Workbook, tenant: Tenant, description: str,
                   rulings: list[Ruling]) -> None:
    sheet = workbook.active
    sheet.title = "Results"
    sheet.cell(row=1, column=1, value=f"LexStream On-Prem report for {tenant.name} "
                                      f"({tenant.tenant_id})")
    # The description repeats the caller's query, so it goes through safe_cell.
    note = f"{description} | {len(rulings)} ruling(s) | {SYNTHETIC_NOTE}"
    sheet.cell(row=2, column=1, value=safe_cell(note))
    write_header(sheet, HEADER_ROW, RESULT_COLUMNS)
    for ruling in rulings:
        append_row(sheet, [
            ruling.docket_id,
            ruling.title,
            ruling.authority,
            ruling.matter.value,
            ruling.decision_date.isoformat(),
            ruling.outcome.value,
            ruling.financial_exposure_gbp,
            "; ".join(ruling.cited_articles),
            ruling.judge_or_inspector,
            ruling.summary_excerpt,
        ])


def _analytics_sheet(workbook: Workbook, analytics: Analytics) -> None:
    sheet = workbook.create_sheet("Analytics")
    sheet.cell(row=1, column=1, value=analytics.disclaimer)
    write_header(sheet, 3, ["Outcome", "Rulings", "Percent"])
    for share in analytics.outcome_distribution:
        append_row(sheet, [share.outcome.value, share.count, share.percent])
    append_row(sheet, [])
    append_row(sheet, ["Total exposure (GBP)", analytics.exposure.total_gbp])
    # Written as text so the exact decimal survives; a float cell could round it.
    append_row(sheet, ["Median exposure (GBP)", str(analytics.exposure.median_gbp)])
    append_row(sheet, ["Highest exposure (GBP)", analytics.exposure.highest_gbp])
    append_row(sheet, [])
    append_row(sheet, ["Most cited clauses", "Citations"])
    for clause in analytics.top_clauses:
        append_row(sheet, [clause.article, clause.count])


def _trend_sheet(workbook: Workbook, analytics: Analytics) -> None:
    sheet = workbook.create_sheet("Authority trend")
    write_header(sheet, 1, ["Authority", "Year", "Rulings", "Upheld or compliance order",
                            "Percent", "Direction"])
    for trend in analytics.authority_trend:
        for point in trend.by_year:
            append_row(sheet, [trend.authority, point.year, point.rulings,
                               point.upheld_or_ordered, point.percent, trend.direction])


def report_bytes(tenant: Tenant, description: str, rulings: list[Ruling],
                 analytics: Analytics) -> bytes:
    """Results and analytics of one query. Every row belongs to ``tenant``."""
    workbook = Workbook()
    _results_sheet(workbook, tenant, description, rulings)
    _analytics_sheet(workbook, analytics)
    _trend_sheet(workbook, analytics)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
