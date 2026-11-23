"""Exercise the UI in Chromium using isolated, explicitly synthetic records.

Run from the repository root with requirements-browser.txt installed. Requests
are fulfilled through Flask's test client; no server or real database is used.
The optional --screenshots flag saves the database-independent overview only.
"""

import argparse
from pathlib import Path
import re
import sys
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright

import app as application_module
from test_pages import TABLE_ROUTES


def fixture_query(sql, parameters=()):
    """Fixed UI examples. These values never represent experiment measurements."""
    if sql == application_module.CALORIMETER_SQL:
        records = [(f"SAMPLE-{i:02d}", 1000 + i, i, "1-12", 10, i % 5 + 1, 35.0 + i / 10)
                   for i in range(54) if i != 20]
        records.append(("DUPLICATE-SAMPLE", 999, 30, None, None, None, None))
        return records, []
    if sql == "SELECT height FROM gluing_progress":
        return [(3.0 + i / 25,) for i in range(25)] + [(None,), (float("nan"),)], []
    if "COUNT(*)" in sql:
        return [(101,)], []
    if "FROM sipm_qc_result" in sql:
        offset = parameters[-1]
        return [(i + 1, 1, "2000-01-01", 100 + i, 50.0, 0.1, 20.0, 1, i / 10)
                for i in range(offset, min(offset + 50, 101))], []
    table = re.search(r"\bFROM\s+(\w+)", sql, re.IGNORECASE).group(1)
    if table == "sipm":
        return [(10, "Sample ten"), (2, "Sample two"), (1, "Sample one")], []
    row = next(row for _, name, row in TABLE_ROUTES if name == table)
    columns = [f"sample_column_{i}" for i in range(len(row))]
    return [row], columns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", action="store_true")
    parser.add_argument("--browser-path", help="Optional path to an existing Chromium executable")
    args = parser.parse_args()
    app = application_module.create_app({"TESTING": True, "DB_USER": "", "DB_NAME": ""})
    client = app.test_client()
    page_errors, external_requests = [], []
    checks = 0

    def respond(route):
        target = urlsplit(route.request.url)
        if target.netloc != "webdevflask.test":
            external_requests.append(route.request.url)
            route.abort()
            return
        response = client.open(target.path + ("?" + target.query if target.query else ""),
                               method=route.request.method)
        body = response.data
        if response.mimetype == "text/html" and target.path not in {"/", "/circle"}:
            body = body.replace(b'<main id="main-content" tabindex="-1">',
                                b'<main id="main-content" tabindex="-1">'
                                b'<p class="notice">Synthetic test fixtures: not experiment data.</p>')
        headers = dict(response.headers)
        headers.pop("Content-Length", None)
        route.fulfill(status=response.status_code, headers=headers, body=body)

    paths = list(dict.fromkeys(["/", "/circle", "/histogram", "/calo_vis/1",
                               "/sipmQC", "/sipmQC/3", *[item[0] for item in TABLE_ROUTES]]))
    with patch("app.query", side_effect=fixture_query), sync_playwright() as playwright:
        launch_options = {"executable_path": args.browser_path} if args.browser_path else {"channel": "chromium"}
        browser = playwright.chromium.launch(**launch_options)
        try:
            for width, height in [(1440, 1000), (390, 844), (320, 740)]:
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=2)
                context.route("**/*", respond)
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                for path in paths:
                    response = page.goto("http://webdevflask.test" + path, wait_until="networkidle")
                    assert response.status == 200, (path, response.status)
                    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                    assert not overflow, f"Page overflow: {path} at {width}px"
                    assert page.locator("main h1").count() == 1, (path, "page heading")
                    checks += 1
                    if args.screenshots and path == "/" and width in {1440, 390}:
                        filename = "overview-desktop.png" if width == 1440 else "overview-mobile.png"
                        (ROOT / "docs/screenshots").mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(ROOT / "docs/screenshots" / filename), full_page=True)

                page.goto("http://webdevflask.test/sipm", wait_until="networkidle")
                table_rows = page.locator("[data-record-row]")
                sort_button = page.get_by_role("button", name="Sort by SiPM ID", exact=True)
                sort_button.focus()
                page.keyboard.press("Enter")
                assert [text.strip() for text in table_rows.locator("td:first-child").all_text_contents()] == ["1", "2", "10"]
                page.keyboard.press("Enter")
                assert [text.strip() for text in table_rows.locator("td:first-child").all_text_contents()] == ["10", "2", "1"]
                search = page.get_by_label("Filter displayed rows")
                search.fill("Sample two")
                assert page.locator("[data-record-row]:visible").count() == 1
                search.fill("not-a-record")
                assert page.locator("[data-record-row]:visible").count() == 0
                assert page.get_by_text("No displayed rows match your filter.", exact=False).is_visible()
                search.fill("")
                assert page.locator("[data-record-row]:visible").count() == 3
                page.goto("http://webdevflask.test/sipmQC", wait_until="networkidle")
                page.get_by_role("link", name="Last", exact=True).click()
                assert page.locator("[data-record-row]").count() == 1
                assert "Page 3 of 3" in page.locator(".table-footer").inner_text()
                page.get_by_role("link", name="Previous", exact=True).click()
                assert page.locator("[data-record-row]").count() == 50
                page.goto("http://webdevflask.test/calo_vis/1", wait_until="networkidle")
                assert page.locator(".calo-cell").count() == 54
                assert page.locator(".calo-cell-duplicate").count() == 1
                assert page.locator(".calo-cell-missing").count() == 1
                if width < 700:
                    assert page.locator(".calo-scroll").evaluate("e => e.scrollWidth > e.clientWidth")
                context.close()
        finally:
            browser.close()
    assert not page_errors, page_errors
    assert not external_requests, external_requests
    print(f"PASS: {checks} route/viewport checks; keyboard sorting, filtering, pagination, "
          "and fixed geometry at 1440/390/320px; no JavaScript errors or external requests.")


if __name__ == "__main__":
    main()
