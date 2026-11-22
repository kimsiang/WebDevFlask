"""Histogram rendering must tolerate incomplete measurements."""

from decimal import Decimal
import math

import pytest

from conftest import Result


@pytest.mark.parametrize("rows,valid,skipped", [
    ((), 0, 0),
    (((None,), (float("nan"),), (float("inf"),), (-float("inf"),), ("invalid",)), 0, 5),
    (((1.0,), (1.5,), (Decimal("2.0"),), ("2.5",), (None,), (float("nan"),)), 4, 2),
    (((3.0,), (3.0,), (3.0,)), 3, 0),
])
def test_histogram_handles_missing_nonfinite_and_constant_values(app, database_stub, capture_templates, rows, valid, skipped):
    database_stub.queue(Result(rows=rows))
    with capture_templates(app) as rendered:
        response = app.test_client().get("/histogram")
    assert response.status_code == 200
    context = rendered[-1][1]
    assert context["count"] == valid
    assert context["skipped"] == skipped
    assert sum(item["count"] for item in context["bins"]) == valid
    for item in context["bins"]:
        assert math.isfinite(item["left"])
        assert math.isfinite(item["right"])
        assert item["left"] < item["right"]
        assert isinstance(item["count"], int)
        assert item["count"] >= 0
    assert "cdn.pydata.org" not in response.get_data(as_text=True)


def test_histogram_keeps_both_extreme_measurements(app, database_stub, capture_templates):
    database_stub.queue(Result(rows=((0.0,), (10.0,))))
    with capture_templates(app) as rendered:
        response = app.test_client().get("/histogram")
    assert response.status_code == 200
    bins = rendered[-1][1]["bins"]
    assert bins[0]["left"] <= 0.0
    assert bins[-1]["right"] >= 10.0
    assert bins[0]["count"] == 1
    assert bins[-1]["count"] == 1
    assert sum(item["count"] for item in bins) == 2
