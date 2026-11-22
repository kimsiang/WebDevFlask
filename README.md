# WebDevFlask

A read-only Flask viewer for the Muon g-2 calorimeter database: detector inventory, quality-control results, assembly records, and calorimeter channel maps.

The application uses the existing MySQL database. This repository does **not** contain its data, schema definition, credentials, or an authentication service. Access to the original database requires the appropriate Fermilab network access and a database account. The home page can be opened without a database connection; data pages report a controlled service-unavailable response when the database is unavailable.

## Features

| Area | Pages |
| --- | --- |
| Detector inventory | Calorimeters, SiPMs, crystals, fibers, and front panels |
| Electronics inventory | BeagleBones, BK Precision supplies, WFD5, MicroTCA, and AMC13 |
| Quality control | SiPM LED runs, crystal measurements, and pentapus cable results |
| Assembly | Crystal–SiPM gluing records, channel maps, and a height histogram |
| Laboratory support | Existing g-Brew records |

Tables support keyboard-accessible sorting and text search over the rows loaded on the current page. SiPM QC uses server-side pagination with 50 records per page; filtering a page does not search other pages. The interface uses local assets and supports narrow screens and printing.

Existing data-viewing URLs are preserved, including `/sipmQC`, `/gluingProgress`, `/calo_vis/<number>`, and both `/pentapusQC` and `/pentapus_qc`.

## Quick start

Use Python 3.11 or newer.

```bash
git clone https://github.com/kimsiang/WebDevFlask.git
cd WebDevFlask
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:8888](http://127.0.0.1:8888). The local development server binds to the loopback interface with debug mode disabled.

Configure the database before opening a data page. Supply these variables through your shell or deployment environment; no credentials belong in source control. `.env.example` lists the supported settings for reference; the application does not automatically load `.env` files.

```bash
export DB_HOST='your-database-host'
export DB_PORT='3306'
export DB_USER='your-read-only-user'
export DB_NAME='your-existing-database'
# Set DB_PASSWORD through your shell or deployment secret configuration.
python app.py
```

The database account needs `SELECT` access to the tables listed in [the maintenance notes](docs/maintenance.md#database-contract). The application does not create tables, seed records, run migrations, or change production data.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DB_HOST` | `127.0.0.1` | MySQL hostname |
| `DB_PORT` | `3306` | MySQL TCP port |
| `DB_USER` | Empty | Required database username |
| `DB_PASSWORD` | Empty | Database password |
| `DB_NAME` | Empty | Required existing database name |
| `DB_CONNECT_TIMEOUT` | `5` | Connection timeout in seconds |
| `DB_READ_TIMEOUT` | `10` | Read timeout in seconds |
| `DB_WRITE_TIMEOUT` | `10` | Write timeout in seconds |
| `DB_SSL_CA` | Empty | Optional CA certificate path; enables certificate and hostname verification for MySQL TLS |

Importing `app.py` does not connect to MySQL. Each request opens a connection only if it needs database data, and that connection is closed when the request finishes. Missing `DB_USER` or `DB_NAME` produces a service-unavailable response before a connection is attempted. The application factory, `create_app(config=None)`, supports isolated test configuration; `app:app` is the WSGI entry point.

## Development and tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

The regression suite uses fake DB-API connections and controlled rows. It covers route responses, connection cleanup, query parameters, pagination boundaries, malformed measurements, and template output without requiring MySQL or network access. SQLite checks additionally exercise query behavior against small controlled datasets; they do not validate MySQL compatibility or the production schema.

These tests do not replace an integration check against the deployed database. Its schema, constraints, indexes, data volume, and current measurement conventions are not included here. See [validation and operational limits](docs/maintenance.md#validation-and-operational-limits).

Optional JavaScript interaction checks use the real table template and script in
an in-process DOM, without opening a browser or contacting a database:

```bash
npm --prefix tests/js ci --ignore-scripts
npm --prefix tests/js test
```

Activate the Python virtual environment first. See [the DOM test notes](tests/js/README.md)
for supported Node versions and the `PYTHON` interpreter override.

The optional Chromium check exercises all data pages at 1440, 390, and 320 px,
plus keyboard sorting, filtering, pagination, and channel-map geometry. It serves
synthetic fixtures through the Flask test client, with no live database:

```bash
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
python scripts/check_browser.py
# Optional: save desktop and phone screenshots of the overview.
python scripts/check_browser.py --screenshots
```

An existing Chromium executable can be selected with `--browser-path /path/to/chromium`.
This script was syntax-checked during this review; its full browser run was blocked
by the execution environment. Browser layout and screenshots remain unverified.

## Deployment

Use a production WSGI server to load `app:app`, and configure the database variables in that service's environment. For example, on a Unix host:

```bash
python -m pip install -r requirements-prod.txt
gunicorn --bind 127.0.0.1:8888 app:app
```

Configure the site's existing authenticated reverse proxy to forward to that local port. `python app.py` is for local development. These commands do not install or configure the site's proxy or authentication.

Keep the viewer behind the intended institutional network and authentication boundary. The application supplies no login or access-control layer, and inventory pages can contain host addresses and operational notes. Use a database account restricted to reads. Database credentials and exceptions are not displayed in the error page.

The old sign-up prototype did not create accounts or provide authentication. Its form has been retired; `/showSignUp` and POST requests to `/signUp` return HTTP 410 with a read-only notice. The unused PHP updater has also been removed; editing database records is outside this viewer's scope.

## Repository guide

| Path | Responsibility |
| --- | --- |
| `app.py` | Application factory, queries, routes, and data preparation |
| `db.py` | Environment configuration and request-scoped database lifecycle |
| `charts.py` | Histogram preparation using the Python standard library |
| `templates/` | Shared layout, inventory/QC tables, visualizations, and error pages |
| `static/` | Local styles, scripts, and images |
| `tests/` | Regression tests using controlled database responses |
| `requirements.txt` | Runtime dependencies |
| `requirements-dev.txt` | Development and test dependencies |
| `requirements-prod.txt` | Production server dependencies |
| `requirements-browser.txt` | Optional Playwright test dependencies |
| `scripts/check_browser.py` | Browser checks with synthetic fixtures |
| `tests/js/` | Optional DOM interaction tests and locked Node dependencies |
| `.env.example` | Example configuration values; not loaded automatically |
| `docs/maintenance.md` | Review findings, database assumptions, and integration checks |

## Data interpretation

The viewer displays stored database values. Units are not inferred where the original schema and templates did not establish them. The pentapus column labelled “Mean ≥ 98” preserves the original numerical criterion; it is not a newly validated acceptance test. Calorimeter maps and QC selections retain the historical filtering assumptions, documented in the maintenance notes.
