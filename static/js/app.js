"use strict";

// Enhance server-rendered tables without changing the records or requiring a CDN.
document.querySelectorAll("[data-records-table]").forEach((table) => {
  const panel = table.closest(".data-panel");
  const body = table.tBodies[0];
  const rows = Array.from(body.querySelectorAll("[data-record-row]"));
  const filter = panel.querySelector("[data-table-filter]");
  const status = panel.querySelector("[data-row-count]");
  const empty = panel.querySelector("[data-filter-empty]");
  const headers = Array.from(table.tHead.rows[0].cells);
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
  const originalOrder = new Map(rows.map((row, index) => [row, index]));
  const searchText = new Map(rows.map((row) => [row, row.textContent.toLocaleLowerCase().replace(/\s+/g, " ")]));
  let sortMessage = "";

  const updateFilter = () => {
    const query = filter.value.trim().toLocaleLowerCase().replace(/\s+/g, " ");
    let visible = 0;
    rows.forEach((row) => {
      row.hidden = !searchText.get(row).includes(query);
      if (!row.hidden) visible += 1;
    });
    status.textContent = `${visible} of ${rows.length} loaded rows displayed${sortMessage}`;
    empty.hidden = visible > 0 || rows.length === 0;
  };

  const cellValue = (row, column) => {
    const cell = row.cells[column];
    return cell && !cell.querySelector(".missing") ? cell.textContent.trim() : "";
  };

  const numericValue = (value) => {
    if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(value)) return null;
    const number = Number(value);
    if (!Number.isFinite(number)) return null;
    // Long integer identifiers must not be rounded to an unsafe JS number.
    if (Number.isInteger(number) && !Number.isSafeInteger(number)) return null;
    return number;
  };

  headers.forEach((header, column) => {
    const label = header.textContent.trim();
    const button = document.createElement("button");
    button.type = "button";
    button.className = "sort-button";
    button.setAttribute("aria-label", `Sort by ${label}`);
    button.append(document.createTextNode(label));
    const icon = document.createElement("span");
    icon.className = "sort-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "↕";
    button.append(icon);
    header.replaceChildren(button);
    header.setAttribute("aria-sort", "none");

    button.addEventListener("click", () => {
      const ascending = header.getAttribute("aria-sort") !== "ascending";
      const direction = ascending ? 1 : -1;
      const sortedRows = [...rows].sort((a, b) => {
        const av = cellValue(a, column);
        const bv = cellValue(b, column);
        if (!av && bv) return 1;
        if (av && !bv) return -1;
        const an = numericValue(av);
        const bn = numericValue(bv);
        const comparison = an !== null && bn !== null ? an - bn : collator.compare(av, bv);
        return direction * comparison || originalOrder.get(a) - originalOrder.get(b);
      });
      sortedRows.forEach((row) => body.append(row));
      headers.forEach((other) => {
        other.setAttribute("aria-sort", "none");
        other.querySelector(".sort-icon").textContent = "↕";
      });
      header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
      icon.textContent = ascending ? "↑" : "↓";
      sortMessage = ` · Sorted by ${label}, ${ascending ? "ascending" : "descending"}`;
      updateFilter();
    });
  });

  filter.addEventListener("input", updateFilter);
  filter.disabled = rows.length === 0;
  panel.querySelector("[data-table-toolbar]").hidden = false;
  updateFilter();
});
