"""SiPM QC pagination boundaries, including an incomplete final page."""

import pytest

from conftest import Result


@pytest.mark.parametrize("count,pages", [(0, 1), (1, 1), (50, 1), (51, 2), (100, 2), (101, 3)])
def test_first_page_has_exact_page_count(app, database_stub, capture_templates, count, pages):
    database_stub.queue(Result(rows=((count,),)), Result())
    with capture_templates(app) as rendered:
        response = app.test_client().get("/sipmQC")
    assert response.status_code == 200
    context = rendered[-1][1]
    assert context["page"] == 1
    assert context["total_pages"] == pages
    assert context["total_entries"] == count
    assert context["per_page"] == 50


def test_incomplete_last_page_is_accessible(app, database_stub, capture_templates):
    row = (101, 1, "2017-01-01", 7, 55, 0.01, 20, 2, 30)
    database_stub.queue(Result(rows=((101,),)), Result(rows=(row,)))
    with capture_templates(app) as rendered:
        response = app.test_client().get("/sipmQC/3")
    assert response.status_code == 200
    context = rendered[-1][1]
    assert context["page"] == 3
    assert context["total_pages"] == 3
    assert tuple(context["rows"]) == (row,)
    query = database_stub.connections[0].queries[-1]
    assert "LIMIT" in query[0].upper()
    assert "%s" in query[0]
    assert "LIMIT %s OFFSET %s" in query[0]
    assert query[1][-2:] == (50, 100)


@pytest.mark.parametrize("count,page", [(0, 2), (1, 2), (50, 2), (51, 3), (100, 3), (101, 4)])
def test_out_of_range_page_is_404(app, database_stub, count, page):
    database_stub.queue(Result(rows=((count,),)))
    response = app.test_client().get(f"/sipmQC/{page}")
    assert response.status_code == 404
    assert database_stub.connections[0].closed
    assert len(database_stub.connections[0].queries) == 1


@pytest.mark.parametrize("page", ["0", "-1", "invalid", "1%20OR%201=1"])
def test_invalid_page_is_rejected_before_database_access(app, database_stub, page):
    assert app.test_client().get(f"/sipmQC/{page}").status_code == 404
    assert database_stub.connect_calls == []
