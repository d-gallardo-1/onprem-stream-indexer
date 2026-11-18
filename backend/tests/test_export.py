"""The .xlsx report: it opens, matches the query and neutralises formula cells."""

from __future__ import annotations

import io
import zipfile
from datetime import date

import pytest
from openpyxl import load_workbook

from app.analytics.summary import summarise
from app.data.corpus import default_rulings
from app.data.tenants import LAW as LAW_PROFILE
from app.workbook.exporter import HEADER_ROW, RESULT_COLUMNS, report_bytes
from app.workbook.layout import safe_cell

from .conftest import API, LAW, dockets

EXPORT = f"{API}/export/analytics-xlsx"


def open_report(client, **params):
    response = client.get(EXPORT, params={"tenant_id": LAW, **params})
    assert response.status_code == 200
    return response, load_workbook(io.BytesIO(response.content))


def test_report_is_a_valid_workbook_with_three_sheets(client):
    response, workbook = open_report(client)

    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert response.headers["content-disposition"] == (
        'attachment; filename="lexstream_report_TNT-LAW-01.xlsx"')
    assert zipfile.ZipFile(io.BytesIO(response.content)).testzip() is None
    assert workbook.sheetnames == ["Results", "Analytics", "Authority trend"]
    assert [cell.value for cell in workbook["Results"][HEADER_ROW]] == list(RESULT_COLUMNS)


def test_rows_and_figures_match_the_same_query_on_the_api(client):
    params = {"q": "costs", "outcome": "SETTLED_WITH_COSTS"}
    snapshot = client.get(f"{API}/search/snapshot", params={"tenant_id": LAW, **params}).json()
    _, workbook = open_report(client, **params)
    rows = list(workbook["Results"].iter_rows(min_row=HEADER_ROW + 1, values_only=True))
    figures = {row[0]: row[1] for row in workbook["Analytics"].iter_rows(values_only=True)
               if row[0]}

    assert [row[0] for row in rows] == dockets(snapshot)
    assert sum(row[6] for row in rows) == snapshot["analytics"]["exposure"]["total_gbp"]
    assert all(isinstance(row[6], int) for row in rows)  # money stays a whole number
    assert figures["Total exposure (GBP)"] == snapshot["analytics"]["exposure"]["total_gbp"]
    assert figures["Median exposure (GBP)"] == snapshot["analytics"]["exposure"]["median_gbp"]
    assert figures["SETTLED_WITH_COSTS"] == len(rows) and figures["UPHELD"] == 0
    assert "Query: costs | Outcome: SETTLED_WITH_COSTS" in workbook["Results"]["A2"].value
    assert f"{len(rows)} ruling(s)" in workbook["Results"]["A2"].value


def test_report_states_that_the_data_is_synthetic_and_not_advice(client):
    _, workbook = open_report(client)

    assert "Synthetic demo data" in workbook["Results"]["A2"].value
    assert "not legal advice" in workbook["Analytics"]["A1"].value


def test_trend_sheet_has_one_row_per_authority_and_year(client):
    snapshot = client.get(f"{API}/search/snapshot", params={"tenant_id": LAW}).json()
    _, workbook = open_report(client)
    expected = sum(len(trend["by_year"]) for trend in snapshot["analytics"]["authority_trend"])

    assert workbook["Authority trend"].max_row == expected + 1


def test_an_empty_result_still_gives_a_workbook(client):
    _, workbook = open_report(client, q="zeppelin")

    assert workbook["Results"].max_row == HEADER_ROW
    assert "0 ruling(s)" in workbook["Results"]["A2"].value


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_text_that_starts_like_a_formula_is_neutralised(prefix):
    assert safe_cell(f"{prefix}SUM(A1:A9)") == f"'{prefix}SUM(A1:A9)"


def test_numbers_and_ordinary_text_pass_through():
    assert safe_cell(-250) == -250 and safe_cell(12.5) == 12.5
    assert safe_cell("Corvane Freight v Lumestra Packaging") == (
        "Corvane Freight v Lumestra Packaging")


def test_a_hostile_ruling_cannot_place_a_formula_in_the_report():
    hostile = default_rulings(LAW_PROFILE)[0].model_copy(update={
        "title": '=HYPERLINK("http://evil.example","open")',
        "judge_or_inspector": "@SUM(1+1)",
        "summary_excerpt": "+cmd|' /C calc'!A0",
        "cited_articles": ["-2+3", "COC art. 14"],
        "decision_date": date(2025, 1, 1),
    })
    payload = report_bytes(LAW_PROFILE.tenant, "Query: (all rulings)", [hostile],
                           summarise([hostile]))

    sheet = load_workbook(io.BytesIO(payload))["Results"]
    cells = [cell for row in sheet.iter_rows(min_row=HEADER_ROW + 1) for cell in row]

    assert all(cell.data_type != "f" for cell in cells)  # no cell is a formula
    values = [cell.value for cell in cells]
    assert values[1].startswith("'=HYPERLINK") and values[8] == "'@SUM(1+1)"
    assert values[9].startswith("'+cmd") and values[7] == "'-2+3; COC art. 14"
    clauses = load_workbook(io.BytesIO(payload))["Analytics"]
    assert "'-2+3" in [row[0] for row in clauses.iter_rows(values_only=True)]
