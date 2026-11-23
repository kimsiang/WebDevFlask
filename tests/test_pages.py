"""Request-level regression tests for the historical database views."""

from html.parser import HTMLParser

import pytest

from conftest import Result


class Tables(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = {"headers": [], "rows": []}
            self.tables.append(self.table)
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"th", "td"} and self.row is not None:
            self.cell = [tag, []]

    def handle_data(self, data):
        if self.cell is not None:
            self.cell[1].append(data)

    def handle_endtag(self, tag):
        if tag in {"th", "td"} and self.cell is not None:
            self.row.append(" ".join("".join(self.cell[1]).split()))
            if self.cell[0] == "th":
                self.table["headers"].append(self.row[-1])
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row and self.row != self.table["headers"]:
                self.table["rows"].append(self.row)
            self.row = None
        elif tag == "table":
            self.table = None


# A distinct value for every column catches swapped/unpacked fields while
# exercising each real template (not merely whether the SQL can be dispatched).
TABLE_ROUTES = [
    ("/calorimeter", "calorimeter", (1, "2016-10-01")),
    ("/sipm", "sipm", (10, "PKG-20")),
    ("/crystalQC", "crystal_qc", (1, "XTAL-2", "LAB", 3.1, 3.2, 4.1, 4.2, 14.0, 0.91)),
    ("/pentapusQC", "pentapus_qc", (1, 49.1, 49.2, 49.3, 49.4, 49.5, 49.3, 0.4)),
    ("/pentapus_qc", "pentapus_qc", (1, 49.1, 49.2, 49.3, 49.4, 49.5, 49.3, 0.4)),
    ("/gluingProgress", "gluing_progress", (1, 1, "XTAL-2", 10, 3.1, 3.2, "1-12", 20, 2, 0, "2016-10-01", "2016-10-02")),
    ("/beaglebone", "beaglebone", (1, "192.0.2.1")),
    ("/bkprecision", "bkprecision", (1, "BK-100", 2)),
    ("/amc13", "amc13", (1, "vendor", "model", "lab", "owner", "installed", "T2", "T1", "ready", "note")),
    ("/microtca", "utca_crate", (1, "vendor", "model", "lab", "owner", "v1", "installed", "note")),
    ("/wfd5", "wfd5", (1, "PS-2", "AFE-3", "installed", "1", "2", "3", "4", "lab", "owner", "ready")),
    ("/gbrew", "g_brew", ("Researcher", 2, 3.5)),
    ("/fiber", "fiber", (1, 2, 3.5, 4)),
    ("/panel", "front_panel", (1, 2, 3.5, 4.5)),
]


@pytest.mark.parametrize("path,table,row", TABLE_ROUTES)
def test_existing_table_routes_render_and_close_connection(app, database_stub, path, table, row):
    database_stub.queue(Result(rows=(row,), columns=tuple(f"column_{i}" for i in range(len(row)))))
    response = app.test_client().get(path)
    assert response.status_code == 200
    assert database_stub.connections
    connection = database_stub.connections[-1]
    assert connection.closed
    assert all(cursor.closed for cursor in connection.cursors)
    assert all(sql.lstrip().upper().startswith("SELECT") for sql, _ in connection.queries)
    assert any(table in sql.lower() for sql, _ in connection.queries)
    assert connection.commits == 0
    assert b"<table" in response.data


@pytest.mark.parametrize("path,table,row", TABLE_ROUTES)
def test_empty_tables_have_a_useful_state(app, database_stub, path, table, row):
    database_stub.queue(Result())
    response = app.test_client().get(path)
    assert response.status_code == 200
    text = response.get_data(as_text=True).lower()
    assert "no records" in text or "no data" in text


def test_database_values_are_escaped(app, database_stub):
    payload = '<script>alert("database-value")</script>'
    database_stub.queue(Result(rows=((10, payload),)))
    response = app.test_client().get("/sipm")
    assert response.status_code == 200
    assert payload not in response.get_data(as_text=True)
    assert "&lt;script&gt;" in response.get_data(as_text=True)


def test_crystal_dimensions_match_their_column_headings(app, database_stub):
    row = (1, "XTAL-2", "LAB", 3.1, 3.2, 4.1, 4.2, 14.0, 0.91)
    database_stub.queue(Result(rows=(row,)))
    response = app.test_client().get("/crystalQC")
    assert response.status_code == 200
    table = Tables(response.get_data(as_text=True)).tables[0]
    record = dict(zip(table["headers"], table["rows"][0]))
    assert record["WidthLeft"] == "3.1"
    assert record["WidthRight"] == "3.2"
    assert record["HeightLeft"] == "4.1"
    assert record["HeightRight"] == "4.2"


def test_separate_requests_do_not_share_cursors_or_connections(app, database_stub):
    database_stub.queue(Result(rows=((1, "first"),)))
    database_stub.queue(Result(rows=((2, "second"),)))
    client = app.test_client()
    assert client.get("/sipm").status_code == 200
    assert client.get("/sipm").status_code == 200
    first, second = database_stub.connections
    assert first is not second
    assert first.closed and second.closed
    assert first.cursors[0] is not second.cursors[0]
    assert first.cursors[0].closed and second.cursors[0].closed
