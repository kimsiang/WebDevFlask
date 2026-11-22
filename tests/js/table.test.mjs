import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { JSDOM } from "jsdom";

const script = readFileSync(new URL("../../static/js/app.js", import.meta.url), "utf8");
const fixtureRenderer = fileURLToPath(new URL("render_fixture.py", import.meta.url));

function page(t, headers, rows) {
  const rendered = spawnSync(process.env.PYTHON || "python", [fixtureRenderer], {
    input: JSON.stringify({ headers, rows }),
    encoding: "utf8",
  });
  assert.equal(rendered.status, 0, `Fixture rendering failed: ${rendered.stderr || rendered.error}`);
  // No resources option: jsdom cannot fetch external styles, scripts, or pages.
  // Evaluate only the repository's table enhancement against actual Jinja output.
  const dom = new JSDOM(rendered.stdout, { runScripts: "outside-only" });
  t.after(() => dom.window.close());
  dom.window.eval(script);
  return dom.window;
}

function values(window, column = 0, visibleOnly = false) {
  return [...window.document.querySelectorAll("[data-record-row]")]
    .filter((row) => !visibleOnly || !row.hidden)
    .map((row) => row.cells[column].textContent.trim());
}

function sort(window, column = 0) {
  window.document.querySelectorAll(".sort-button")[column].click();
}

function filter(window, text) {
  const field = window.document.querySelector("[data-table-filter]");
  field.value = text;
  field.dispatchEvent(new window.Event("input", { bubbles: true }));
}

test("numeric values sort in ascending and descending order", (t) => {
  const window = page(t, ["Value"], [[10], [-2], [2.5], [0]]);
  sort(window);
  assert.deepEqual(values(window), ["-2", "0", "2.5", "10"]);
  sort(window);
  assert.deepEqual(values(window), ["10", "2.5", "0", "-2"]);
});

test("text sorting ignores case and keeps natural identifier order", (t) => {
  const window = page(t, ["Channel"], [["channel10"], ["Channel2"], ["alpha"]]);
  sort(window);
  assert.deepEqual(values(window), ["alpha", "Channel2", "channel10"]);
  sort(window);
  assert.deepEqual(values(window), ["channel10", "Channel2", "alpha"]);
});

test("scientific notation sorts by measured numeric value", (t) => {
  const window = page(t, ["Current"], [["2e-3"], ["-1.5e2"], ["3E+1"], ["0.01"]]);
  sort(window);
  assert.deepEqual(values(window), ["-1.5e2", "2e-3", "0.01", "3E+1"]);
  sort(window);
  assert.deepEqual(values(window), ["3E+1", "0.01", "2e-3", "-1.5e2"]);
});

test("missing measurements remain last in both directions", (t) => {
  const window = page(t, ["Value", "Record"], [[null, "missing"], [5, "five"], [1, "one"]]);
  sort(window);
  assert.deepEqual(values(window, 1), ["one", "five", "missing"]);
  sort(window);
  assert.deepEqual(values(window, 1), ["five", "one", "missing"]);
});

test("equal values keep original record order through repeated sorts", (t) => {
  const window = page(t, ["Value", "Record"], [[2, "first"], [1, "lower"], [2, "second"], [2, "third"]]);
  sort(window);
  assert.deepEqual(values(window, 1), ["lower", "first", "second", "third"]);
  sort(window);
  assert.deepEqual(values(window, 1), ["first", "second", "third", "lower"]);
  sort(window);
  assert.deepEqual(values(window, 1), ["lower", "first", "second", "third"]);
});

test("large integer identifiers sort without floating-point precision loss", (t) => {
  const window = page(t, ["Serial number"], [
    ["9007199254740993"], ["10000000000000000"], ["9007199254740992"], ["9999999999999999"],
  ]);
  sort(window);
  assert.deepEqual(values(window), [
    "9007199254740992", "9007199254740993", "9999999999999999", "10000000000000000",
  ]);
  sort(window);
  assert.deepEqual(values(window), [
    "10000000000000000", "9999999999999999", "9007199254740993", "9007199254740992",
  ]);
});

test("filtering matches any column, announces no results, and clears", (t) => {
  const window = page(t, ["Crystal", "Location"], [
    ["XTAL-1", "North Lab"], ["XTAL-2", "South Lab"], ["XTAL-3", "North Lab"],
  ]);
  const document = window.document;
  const status = document.querySelector("[data-row-count]");
  const empty = document.querySelector("[data-filter-empty]");
  filter(window, "  NORTH   lab  ");
  assert.deepEqual(values(window, 0, true), ["XTAL-1", "XTAL-3"]);
  assert.match(status.textContent, /^2 of 3 loaded rows displayed/);
  assert.equal(empty.hidden, true);
  filter(window, "not present");
  assert.deepEqual(values(window, 0, true), []);
  assert.match(status.textContent, /^0 of 3 loaded rows displayed/);
  assert.equal(empty.hidden, false);
  filter(window, "");
  assert.deepEqual(values(window, 0, true), ["XTAL-1", "XTAL-2", "XTAL-3"]);
  assert.match(status.textContent, /^3 of 3 loaded rows displayed/);
  assert.equal(empty.hidden, true);
});

test("sort controls expose direction and keep filter results intact", (t) => {
  const window = page(t, ["Value", "Location"], [[5, "North"], [1, "South"], [2, "North"]]);
  const document = window.document;
  const headers = [...document.querySelectorAll("thead th")];
  const buttons = [...document.querySelectorAll(".sort-button")];
  const status = document.querySelector("[data-row-count]");
  assert.equal(status.getAttribute("role"), "status");
  assert.equal(status.getAttribute("aria-live"), "polite");
  assert.equal(buttons[0].getAttribute("aria-label"), "Sort by Value");
  assert.deepEqual(headers.map((header) => header.getAttribute("aria-sort")), ["none", "none"]);
  filter(window, "north");
  sort(window);
  assert.deepEqual(values(window, 0, true), ["2", "5"]);
  assert.equal(headers[0].getAttribute("aria-sort"), "ascending");
  assert.match(status.textContent, /^2 of 3 loaded rows displayed · Sorted by Value, ascending$/);
  sort(window);
  assert.equal(headers[0].getAttribute("aria-sort"), "descending");
  assert.deepEqual(values(window, 0, true), ["5", "2"]);
  sort(window, 1);
  assert.deepEqual(headers.map((header) => header.getAttribute("aria-sort")), ["none", "ascending"]);
  assert.match(status.textContent, /Sorted by Location, ascending$/);
});

test("empty tables disable filtering and retain their server empty state", (t) => {
  const window = page(t, ["Value"], []);
  const document = window.document;
  assert.equal(document.querySelector("[data-table-toolbar]").hidden, false);
  assert.equal(document.querySelector("[data-table-filter]").disabled, true);
  assert.match(document.querySelector("[data-row-count]").textContent, /^0 of 0 loaded rows displayed$/);
  assert.equal(document.querySelector("[data-filter-empty]").hidden, true);
  assert.match(document.querySelector(".empty-row").textContent, /No records are available/);
  sort(window);
  assert.deepEqual(values(window), []);
  assert.match(document.querySelector(".empty-row").textContent, /No records are available/);
});
