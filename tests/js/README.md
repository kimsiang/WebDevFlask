# Optional table interaction tests

These nine Node tests execute the repository's actual `static/js/app.js` against
HTML rendered from the shared Jinja table template. They cover sorting, filtering,
missing values, exact ordering of large identifiers, accessible status updates,
and empty tables.

Use a Node version supported by the pinned jsdom release: Node 22.22.2 or later
within 22.x, Node 24.15.0 or later within 24.x, or Node 26+. Install the Python
application dependencies first, then run these commands from the repository root:

```sh
source .venv/bin/activate
npm --prefix tests/js ci --ignore-scripts
npm --prefix tests/js test
```

The fixture renderer uses `python` from the active environment. Set the `PYTHON`
environment variable to an **absolute** interpreter path when using a different
virtual environment.

The tests run in jsdom without opening a browser, binding a port, contacting a
database, or downloading page resources. Python renders each fixture locally.
These are DOM behavior tests; they do not verify browser layout or screenshots.
Node dependencies are confined to this optional test directory and are not
required to run the Flask application.
