"""Optional SOI reference acquisition helpers.

The runtime reads committed YAML. This module is for maintainers refreshing
that reference and should only be imported from acquisition workflows.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Callable

from tax_graph.frontier.soi import parse_soi_label_counts


def fetch_soi_csv_counts(
    url: str,
    *,
    mapping: dict[str, str],
    label_field: str,
    count_field: str,
    fetch_text: Callable[[str], str] | None = None,
) -> dict[str, int]:
    """Fetch and parse a normalized SOI CSV extract.

    ``httpx`` is imported lazily so base-deps runtime commands do not depend on
    the acquisition extra.
    """
    if fetch_text is None:
        import httpx

        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        text = response.text
    else:
        text = fetch_text(url)
    return parse_soi_label_counts(
        list(csv.DictReader(StringIO(text))),
        label_field=label_field,
        count_field=count_field,
        mapping=mapping,
    )
