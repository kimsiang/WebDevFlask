"""Render the real shared table template for optional Node DOM tests."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from flask import render_template
from app import create_app

fixture = json.load(sys.stdin)
application = create_app({"TESTING": True, "DB_USER": "", "DB_NAME": ""})
with application.test_request_context("/"):
    print(render_template(
        "_table.html", title="Fixture records", description="",
        headers=fixture["headers"], rows=fixture["rows"],
        calorimeter_links=False, pentapus_status=False, secondary_table=False,
    ))
