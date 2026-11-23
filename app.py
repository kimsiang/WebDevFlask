"""Read-only Muon g-2 calorimeter database viewer.

Importing this module never contacts MySQL. Use ``create_app`` for isolated
instances, ``flask --app app run`` for development, or ``app:app`` with WSGI.
"""

from collections import defaultdict
from decimal import Decimal, InvalidOperation

from flask import Flask, abort, render_template
import pymysql

from charts import build_histogram
from db import DatabaseUnavailable, close_db, configure_database, query


# Identifiers are fixed application code; request values are bound parameters.
TABLE_VIEWS = (
    ("/calorimeter", "calorimeter", "calorimeter.html",
     "SELECT calorimeter_id, built_date FROM calorimeter ORDER BY calorimeter_id"),
    ("/sipm", "sipm", "sipm.html",
     "SELECT sipm_id, package_id FROM sipm ORDER BY sipm_id"),
    ("/crystalQC", "crystalQC", "crystal_qc.html",
     "SELECT qc_id, serial_number, location, width_left, width_right, "
     "height_left, height_right, length, longitudinal_trans_avg_value "
     "FROM crystal_qc ORDER BY qc_id"),
    ("/gluingProgress", "gluingProgress", "gluing_progress.html",
     "SELECT calo_id, glued, crystal_serial_num, sipm_id, height, width, "
     "breakoutboard, pentapus_cable, pentapus_subcable, calo_xtal_num, "
     "start_time, stop_time FROM gluing_progress ORDER BY calo_id, calo_xtal_num"),
    ("/beaglebone", "beaglebone", "beaglebone.html",
     "SELECT beaglebone_id, ip_address FROM beaglebone ORDER BY beaglebone_id"),
    ("/bkprecision", "bkprecision", "bkprecision.html",
     "SELECT bkprecision_id, serial_number, calorimeter_id "
     "FROM bkprecision ORDER BY bkprecision_id"),
    ("/amc13", "amc13", "amc13.html",
     "SELECT serial_number, vendor, model, location, owner, deployment, "
     "spartan_t2, kintex_t1, status, notes FROM amc13 ORDER BY serial_number"),
    ("/microtca", "microtca", "microtca.html",
     "SELECT serial_number, vendor, model, location, owner, version, deployment, "
     "notes FROM utca_crate ORDER BY serial_number"),
    ("/wfd5", "wfd5", "wfd5.html",
     "SELECT serial_number, wfdps_sn, afe_sn, deployment, mmc_fwv, golden_fwv, "
     "master_fwv, channel_fwv, location, owner, status "
     "FROM wfd5 ORDER BY serial_number"),
    ("/gbrew", "gbrew", "gbrew.html",
     "SELECT name, cups, current_credit FROM g_brew ORDER BY name"),
    ("/fiber", "fiber", "fiber.html",
     "SELECT bundle_id, fiber_id, p_out, prism_id FROM fiber "
     "ORDER BY bundle_id, fiber_id"),
    ("/panel", "panel", "panel.html",
     "SELECT panel_id, bundle_id, bending_close, bending_far "
     "FROM front_panel ORDER BY panel_id, bundle_id"),
)

PENTAPUS_SQL = (
    "SELECT cable_id, impedence_j2, impedence_j3, impedence_j4, impedence_j5, "
    "impedence_j6, mean, max_min FROM pentapus_qc ORDER BY cable_id"
)

# Retain the historical LED / subrun 1 / amplitude < 100 eligibility rule.
# A LEFT JOIN preserves assembly records without eligible QC. Select the highest
# eligible run_no explicitly; do not average or arbitrarily collapse tied runs.
CALORIMETER_SQL = """
SELECT assembly.crystal_serial_num, assembly.sipm_id, assembly.calo_xtal_num,
       assembly.breakoutboard, assembly.pentapus_cable,
       assembly.pentapus_subcable, qc.amp_avg
FROM gluing_progress AS assembly
LEFT JOIN sipm_qc_result AS qc
  ON qc.sipm_id = assembly.sipm_id
 AND qc.run_type = %s AND qc.subrun_no = %s AND qc.amp_avg < %s
 AND qc.run_no = (
     SELECT MAX(recent.run_no)
     FROM sipm_qc_result AS recent
     WHERE recent.sipm_id = assembly.sipm_id
       AND recent.run_type = %s AND recent.subrun_no = %s
       AND recent.amp_avg < %s
 )
WHERE assembly.calo_id = %s
ORDER BY assembly.calo_xtal_num DESC, assembly.crystal_serial_num,
         assembly.sipm_id, qc.amp_avg
"""


def calorimeter_grid(rows):
    """Keep geometry fixed when records are missing, duplicated, or malformed."""
    positions = defaultdict(list)
    invalid_rows = []
    for row in rows:
        try:
            numeric_location = Decimal(str(row[2]).strip())
            valid = (numeric_location.is_finite() and 0 <= numeric_location < 54
                     and numeric_location == numeric_location.to_integral_value())
        except (InvalidOperation, TypeError, ValueError):
            valid = False
        if not valid:
            invalid_rows.append(row)
            continue
        location = int(numeric_location)
        positions[location].append(row)

    grid = []
    # Preserve the legacy DESC + float:right arrangement without assuming which
    # physical side of the detector is being viewed.
    for start in range(45, -1, -9):
        grid_row = []
        for location in range(start, start + 9):
            records = positions[location]
            grid_row.append({
                "location": location,
                "row": records[0] if len(records) == 1 else None,
                "records": records,
                "state": "missing" if not records else "present" if len(records) == 1 else "duplicate",
            })
        grid.append(grid_row)
    return grid, invalid_rows


def create_app(config=None):
    """Create an app without connecting to the experiment database."""
    application = Flask(__name__)
    configure_database(application, config)
    application.teardown_appcontext(close_db)

    @application.after_request
    def response_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        # Detector and infrastructure records should not enter shared caches.
        if response.mimetype == "text/html":
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @application.errorhandler(DatabaseUnavailable)
    @application.errorhandler(pymysql.MySQLError)
    def database_unavailable(error):
        # Never echo connection details, SQL, or credentials to a visitor.
        code = error.args[0] if error.args and isinstance(error.args[0], int) else "unavailable"
        application.logger.warning("Database request failed (%s, %s)", type(error).__name__, code)
        return render_template(
            "error.html", status_code=503, title="Database unavailable",
            message="The database could not be reached or this request could not be completed. "
                    "Check the database configuration and experiment network access, then try again.",
        ), 503

    @application.errorhandler(404)
    def not_found(error):
        return render_template(
            "error.html", status_code=404, title="Page not found",
            message="This page or record range is not available. Choose a section from the navigation.",
        ), 404

    @application.route("/")
    def main():
        return render_template("index.html")

    def table_view(template, sql):
        def show_table():
            rows, col_names = query(sql)
            return render_template(template, rows=rows, col_names=col_names)
        return show_table

    for path, endpoint, template, sql in TABLE_VIEWS:
        application.add_url_rule(path, endpoint, table_view(template, sql))

    @application.route("/sipmQC")
    @application.route("/sipmQC/<int:page>")
    def sipmQC(page=1):
        if page < 1:
            abort(404)
        criteria = "run_type = %s AND sipm_id > 0 AND subrun_no = %s"
        counts, _ = query("SELECT COUNT(*) FROM sipm_qc_result WHERE " + criteria, ("led", 1))
        total_entries = int(counts[0][0])
        per_page = 50
        total_pages = max(1, (total_entries + per_page - 1) // per_page)
        if page > total_pages:
            abort(404)
        rows, _ = query(
            "SELECT run_no, subrun_no, date, sipm_id, volt, curr, temp, gain, amp_avg "
            "FROM sipm_qc_result WHERE " + criteria +
            " ORDER BY run_no, sipm_id, subrun_no, date, volt, curr, temp, gain, amp_avg "
            "LIMIT %s OFFSET %s", ("led", 1, per_page, (page - 1) * per_page),
        )
        page_numbers = sorted({1, total_pages, *range(max(1, page - 2), min(total_pages, page + 2) + 1)})
        return render_template(
            "sipm_qc.html", rows=rows, total_entries=total_entries,
            total_pages=total_pages, page=page, per_page=per_page,
            page_numbers=page_numbers,
        )

    @application.route("/pentapusQC")
    @application.route("/pentapus_qc", endpoint="pentapus_qc")
    def pentapusQC():
        rows, col_names = query(PENTAPUS_SQL)
        return render_template("pentapus_qc.html", rows=rows, col_names=col_names)

    @application.route("/calo_vis/<int:caloNum>")
    def calo_vis(caloNum):
        if not 1 <= caloNum <= 24:
            abort(404)
        rows, col_names = query(CALORIMETER_SQL, ("led", 1, 100, "led", 1, 100, caloNum))
        grid_rows, invalid_rows = calorimeter_grid(rows)
        return render_template(
            "calo_vis.html", rows=rows, col_names=col_names, caloNum=caloNum,
            grid_rows=grid_rows, invalid_rows=invalid_rows,
        )

    @application.route("/histogram")
    def show_histogram():
        rows, _ = query("SELECT height FROM gluing_progress")
        return render_template("histogram.html", **build_histogram(rows))

    @application.route("/circle")
    def circle():
        return render_template("circle.html")

    @application.route("/showSignUp")
    @application.route("/signUp", methods=["POST"])
    def signup_unavailable():
        return render_template(
            "error.html", status_code=410, title="Read-only viewer",
            message="Account registration is not available. This application displays existing "
                    "database records; access is managed by your experiment's network and authentication service.",
        ), 410

    return application


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8888, debug=False)
