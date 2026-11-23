"""Preserve calorimeter geometry and select reproducible QC measurements."""

from decimal import Decimal
import sqlite3

import pytest
import pymysql

from conftest import Result


def test_empty_calorimeter_preserves_all_54_locations(app, database_stub, capture_templates):
    database_stub.queue(Result())
    with capture_templates(app) as rendered:
        response = app.test_client().get("/calo_vis/1")
    assert response.status_code == 200
    grid = rendered[-1][1]["grid_rows"]
    assert len(grid) == 6
    assert all(len(row) == 9 for row in grid)
    assert [cell["location"] for cell in grid[0]] == list(range(45, 54))
    assert [cell["location"] for cell in grid[-1]] == list(range(9))
    assert sorted(cell["location"] for row in grid for cell in row) == list(range(54))
    assert all(cell["state"] == "missing" for row in grid for cell in row)


def test_duplicate_bad_location_and_incomplete_wiring_do_not_shift_map(app, database_stub, capture_templates):
    rows = (
        ("XTAL-A", 1, 5, None, None, None, None),
        ("XTAL-B", 2, 5, "malformed", 1, 2, 30.0),
        ("XTAL-C", 3, 6, "1-12", 2, 3, 40.0),
        ("XTAL-D", 4, 54, "1-1", 2, 4, 45.0),
        ("XTAL-E", 5, None, None, None, None, None),
        ("XTAL-F", 6, -1, None, None, None, None),
        ("XTAL-G", 7, 5.5, None, None, None, None),
    )
    database_stub.queue(Result(rows=rows))
    with capture_templates(app) as rendered:
        response = app.test_client().get("/calo_vis/1")
    assert response.status_code == 200
    context = rendered[-1][1]
    cells = {cell["location"]: cell for row in context["grid_rows"] for cell in row}
    assert len(cells) == 54
    assert cells[5]["state"] == "duplicate"
    assert len(cells[5]["records"]) == 2
    assert cells[6]["state"] == "present"
    assert cells[7]["state"] == "missing"
    assert len(context["invalid_rows"]) == 4
    html = response.get_data(as_text=True)
    for record in rows:
        assert record[0] in html


class SQLiteCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def description(self):
        return self.cursor.description

    def execute(self, sql, parameters=()):
        return self.cursor.execute(sql.replace("%s", "?"), parameters)

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    def close(self):
        self.cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class SQLiteConnection:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)

    def cursor(self):
        return SQLiteCursor(self.connection.cursor())

    def close(self):
        self.connection.close()


def test_calo_query_uses_latest_eligible_run_and_keeps_unmeasured_channels(app, monkeypatch, tmp_path, capture_templates):
    """Execute the actual SELECT against data, rather than matching SQL text.

    SQLite validates query semantics here; live MySQL schema/version compatibility
    is a separate deployment check because the experiment database is unavailable.
    """
    database = tmp_path / "calorimeter.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE gluing_progress (
            crystal_serial_num TEXT, sipm_id INTEGER, calo_xtal_num INTEGER,
            breakoutboard TEXT, pentapus_cable INTEGER, pentapus_subcable INTEGER,
            calo_id INTEGER
        );
        CREATE TABLE sipm_qc_result (
            sipm_id INTEGER, run_no INTEGER, subrun_no INTEGER,
            run_type TEXT, amp_avg REAL
        );
    """)
    connection.executemany("INSERT INTO gluing_progress VALUES (?, ?, ?, ?, ?, ?, ?)", [
        ("LATEST", 100, 53, "1-12", 1, 1, 1),
        ("NO-QC", 101, 52, "1-12", 1, 2, 1),
        ("NO-ELIGIBLE-QC", 102, 51, "1-12", 1, 3, 1),
        ("TIED-RUN", 103, 50, "1-12", 1, 4, 1),
        ("EARLIER-ELIGIBLE", 104, 49, "1-12", 1, 5, 1),
        ("OTHER-CALO", 105, 48, "1-12", 1, 6, 2),
    ])
    connection.executemany("INSERT INTO sipm_qc_result VALUES (?, ?, ?, ?, ?)", [
        (100, 1, 1, "led", 20),
        (100, 5, 1, "led", 25),
        (100, 10, 1, "dark", 30),
        (100, 11, 2, "led", 35),
        (100, 12, 1, "led", 100),
        (102, 1, 1, "dark", 20),
        (103, 7, 1, "led", 40),
        (103, 7, 1, "led", 42),
        (104, 8, 1, "led", 30),
        (104, 9, 1, "led", 120),
        (105, 9, 1, "led", 35),
    ])
    connection.commit()
    connection.close()
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: SQLiteConnection(database))
    with capture_templates(app) as rendered:
        response = app.test_client().get("/calo_vis/1")
    assert response.status_code == 200
    records = rendered[-1][1]["rows"]
    by_crystal = {}
    for record in records:
        by_crystal.setdefault(record[0], []).append(record[-1])
    for values in by_crystal.values():
        if all(value is not None for value in values):
            values.sort()
    assert by_crystal == {
        "LATEST": [25.0],
        "NO-QC": [None],
        "NO-ELIGIBLE-QC": [None],
        "TIED-RUN": [40.0, 42.0],
        "EARLIER-ELIGIBLE": [30.0],
    }


@pytest.mark.parametrize("position", [Decimal("3.0"), 3.0])
def test_integral_numeric_locations_keep_their_geometry(app, database_stub, capture_templates, position):
    record = ("INTEGRAL-POSITION", 12, position, "1-12", 1, 2, 30.0)
    database_stub.queue(Result(rows=(record,)))
    with capture_templates(app) as rendered:
        response = app.test_client().get("/calo_vis/1")
    assert response.status_code == 200
    context = rendered[-1][1]
    cells = {cell["location"]: cell for row in context["grid_rows"] for cell in row}
    assert cells[3]["state"] == "present"
    assert cells[3]["records"] == [record]
    assert context["invalid_rows"] == []
