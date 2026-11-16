"""SQLite FTS5 bm25 scorer for discovery ranking (M15-FR-02).

The index is rebuilt in memory for each search over the already-filtered survivors,
inserted in key order, so scores never depend on catalog insertion order.
"""

from __future__ import annotations

import sqlite3
from typing import Mapping, Sequence

from quati.domain.discovery import fold_text


class Fts5CapabilityIndex:
    def score(self, documents: Mapping[str, str], terms: Sequence[str]) -> dict[str, float]:
        """bm25 per matching document key (lower is better); no terms or no documents match nothing."""
        if not terms or not documents:
            return {}
        connection = sqlite3.connect(":memory:")
        try:
            connection.execute("CREATE VIRTUAL TABLE docs USING fts5(key UNINDEXED, body, "
                               "tokenize='porter unicode61 remove_diacritics 2')")
            connection.executemany("INSERT INTO docs(key, body) VALUES (?, ?)",
                                   [(key, fold_text(documents[key])) for key in sorted(documents)])
            expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)   # always quoted
            rows = connection.execute("SELECT key, bm25(docs) FROM docs WHERE docs MATCH ?", (expression,))
            return {key: float(score) for key, score in rows}
        finally:
            connection.close()


__all__ = ["Fts5CapabilityIndex"]
