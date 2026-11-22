# Maintenance notes

This document records the review of the original application at commit `9f270f8` and the assumptions retained during modernization. The original database and deployment were not available for inspection.

## Review findings

| Finding in the original code | Improvement |
| --- | --- |
| Python 2.7 launch instructions and no dependency manifest | Python 3 setup, explicit runtime/test dependencies, and reproducible commands |
| One global connection and cursor opened during import | Lazy connections scoped to a request and closed at teardown |
| The calorimeter URL value interpolated directly into SQL | Validated calorimeter identifier and parameterized query |
| SiPM QC page counts used division and an extra page | Integer ceiling division with explicit empty and boundary handling |
| Calorimeter QC selection used non-aggregated columns with `GROUP BY` | Highest eligible run number selected explicitly; tied records retained and flagged |
| Crystal width/height values appeared under the opposite left/right headings | Display order aligned with the selected database columns |
| Missing or invalid measurements could break maps or histograms | Missing-data handling and a usable empty state |
| Scripts ran before jQuery loaded; assets depended on external CDNs | Shared local styles/scripts and predictable loading |
| Inactive edit/delete controls and placeholder pagination implied unsupported actions | Read-only tables and working pagination controls |
| The sign-up form suggested account creation but only echoed validation | Retired prototype; no implied authentication |
| An unused PHP file performed SQL updates through GET parameters | Removed from the served static directory |
| The development entry point enabled debug on all network interfaces | Local-only development defaults with debug disabled |

## Database contract

These names come from existing `SELECT` statements. They document what the viewer reads; they are **not** a replacement schema or a proposed migration.

| Table | Columns read |
| --- | --- |
| `calorimeter` | `calorimeter_id`, `built_date` |
| `sipm` | `sipm_id`, `package_id` |
| `sipm_qc_result` | `run_no`, `subrun_no`, `date`, `sipm_id`, `volt`, `curr`, `temp`, `gain`, `amp_avg`; `run_type` is used for filtering |
| `crystal_qc` | `qc_id`, `serial_number`, `location`, `width_left`, `width_right`, `height_left`, `height_right`, `length`, `longitudinal_trans_avg_value` |
| `pentapus_qc` | `cable_id`, `impedence_j2`, `impedence_j3`, `impedence_j4`, `impedence_j5`, `impedence_j6`, `mean`, `max_min` |
| `gluing_progress` | `calo_id`, `glued`, `crystal_serial_num`, `sipm_id`, `height`, `width`, `breakoutboard`, `pentapus_cable`, `pentapus_subcable`, `calo_xtal_num`, `start_time`, `stop_time` |
| `beaglebone` | `beaglebone_id`, `ip_address` |
| `bkprecision` | `bkprecision_id`, `serial_number`, `calorimeter_id` |
| `amc13` | `serial_number`, `vendor`, `model`, `location`, `owner`, `deployment`, `spartan_t2`, `kintex_t1`, `status`, `notes` |
| `utca_crate` | `serial_number`, `vendor`, `model`, `location`, `owner`, `version`, `deployment`, `notes` |
| `wfd5` | `serial_number`, `wfdps_sn`, `afe_sn`, `deployment`, `mmc_fwv`, `golden_fwv`, `master_fwv`, `channel_fwv`, `location`, `owner`, `status` |
| `g_brew` | `name`, `cups`, `current_credit` |
| `fiber` | `bundle_id`, `fiber_id`, `p_out`, `prism_id` |
| `front_panel` | `panel_id`, `bundle_id`, `bending_close`, `bending_far` |

The historical spelling `impedence_*` is retained to match the existing database. The application intentionally does not guess data types, nullability, primary keys, foreign keys, indexes, or default values.

## Scientific and display assumptions

- **SiPM QC list:** LED runs with positive `sipm_id` and `subrun_no = 1`. Pagination is performed by MySQL; client-side search and sorting apply only to the loaded page.
- **Calorimeter geometry:** the original display assumes 24 calorimeters and a 9 × 6 channel layout with positions 0–53. The grid preserves the legacy visual order: 45–53 in the top row, down to 0–8 in the bottom row. The physical viewing side is not verified. Missing positions stay visible as missing; duplicate records are flagged rather than silently choosing one record.
- **Calorimeter QC amplitude:** the map retains LED, first-subrun measurements with `amp_avg < 100` and chooses the highest eligible `run_no` for each SiPM. This is a run-number rule, not an independently verified chronological timestamp. A left join preserves assembly records that have no eligible QC result. All tied QC rows are retained and flagged; amplitudes are not averaged or selected arbitrarily. The `< 100` filter is historical, not a new claim about acceptable amplitudes.
- **Breakout-board labels:** the original HDMI prefix derives from the second component of a hyphenated `breakoutboard` value and a threshold of 10. That convention is not independently verified by hardware documentation.
- **Pentapus flag:** the original `mean >= 98` rule is exposed as a numerical condition. Measurement units and acceptance criteria must be checked against the original QC procedure before interpreting it as pass/fail.
- **Height histogram:** values come from `gluing_progress.height`; missing and non-finite values must not be counted as valid measurements. The column's physical unit is not established by the repository.

## Validation and operational limits

Automated tests use controlled data to exercise the application without opening a production database connection. They can verify error handling, selected query parameters, page boundaries, display labels, and defensive behavior. SQLite checks exercise selection behavior but do not establish MySQL compatibility. These tests cannot establish that the deployed schema, permissions, SQL mode, or detector data agree with these assumptions. Local test commands are provided; no GitHub Actions workflow is added.

Before replacing a live installation:

1. Connect a staging instance to an authorized read-only database account and confirm the listed tables and columns exist.
2. Check the SiPM QC first, last, and partially filled pages against direct database counts.
3. Compare representative calorimeter maps with the established channel layout, especially missing positions, repeated QC runs, and malformed breakout-board values.
4. Check the displayed crystal left/right measurements against source records and confirm the units and historical QC criteria.
5. Exercise large inventory tables on desktop and mobile. Tables other than SiPM QC currently load all matching records. Measure database and browser performance, including the calorimeter query's correlated maximum-run lookup, using the real schema and indexes before adding more data. No index changes have been assumed or applied.
6. Confirm the deployment's network restrictions and authentication boundary, then serve the app through a production WSGI server with its debug mode disabled.

Any schema changes, indexes, account privileges, credentials, deployment authentication, or changes to the scientific selection criteria require information from the database owner. None are inferred or applied by this review.

## Review verification

The November 2026 review verified 74 Python regression cases and nine DOM
interaction cases, including the actual calorimeter selection query against
controlled SQLite records. All active Jinja templates parse, their referenced
local assets exist, JavaScript syntax checks pass, and installed Python
dependencies pass `pip check`.

Native Chromium execution was blocked by the environment's socket restriction;
running it outside that restriction was not approved. No browser layout,
mobile screenshot, or production-database verification is claimed. The optional
browser-check script is retained so those checks can be run in a suitable local
environment before replacing a live installation.

Implementation references: [Flask application contexts and resource cleanup](https://flask.palletsprojects.com/en/stable/appcontext/),
[PyMySQL connections and TLS](https://pymysql.readthedocs.io/en/latest/modules/connections.html),
and [bound cursor parameters](https://pymysql.readthedocs.io/en/latest/modules/cursors.html).
