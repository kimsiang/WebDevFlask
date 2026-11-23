"""Small, dependency-free histogram preparation for database height values."""

from bisect import bisect_right
from math import isfinite


def build_histogram(rows, bin_count=10):
    """Return equal-width bins and count invalid readings without inventing values.

    Bins include the left edge and exclude the right, except for the final bin,
    which includes the largest value. Empty input produces no bins.
    """
    if not isinstance(bin_count, int) or isinstance(bin_count, bool) or bin_count < 1:
        raise ValueError("bin_count must be a positive integer")
    values = []
    skipped = 0
    for row in rows:
        try:
            value = float(row[0])
        except (TypeError, ValueError, OverflowError, IndexError):
            skipped += 1
            continue
        if isfinite(value):
            values.append(value)
        else:
            skipped += 1
    if not values:
        return {"bins": [], "count": 0, "skipped": skipped}

    low, high = min(values), max(values)
    if low == high:
        padding = max(0.5, abs(low) * 0.01)
        lower, upper = low - padding, high + padding
        low = lower if isfinite(lower) else low
        high = upper if isfinite(upper) else high
    # Weighted endpoints avoid overflow in high-low for very large ranges.
    edges = [low * (1 - i / bin_count) + high * (i / bin_count) for i in range(bin_count + 1)]
    counts = [0] * bin_count
    for value in values:
        index = min(bin_count - 1, max(0, bisect_right(edges, value) - 1))
        counts[index] += 1
    bins = [{"left": edges[i], "right": edges[i + 1], "count": counts[i]} for i in range(bin_count)]
    return {"bins": bins, "count": len(values), "skipped": skipped}
