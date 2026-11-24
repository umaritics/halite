import logging
from ._helpers import _now

logger = logging.getLogger(__name__)

SUPERSEDES_METHODS = ("explicit_citation", "model", "human")


def _link_dict(row) -> dict:
    """Link properties with the provenance defaults; links written before provenance existed were model decisions."""
    return {
        "scope": row.get("scope"),
        "confidence": row.get("confidence"),
        "rationale": row.get("rationale"),
        "created_at": row.get("created_at"),
        "method": row.get("method") or "model",
        "model_version": row.get("model_version") or "",
        "decided_by": row.get("decided_by") or "",
        "decided_at": row.get("decided_at") or "",
    }


class IntegrityMixin:
    """Integrity graph operations; preserved from the pre-split implementation."""

    def link_record_supersedes(
        self,
        new_record_id: str,
        old_record_id: str,
        scope: str,
        confidence: float,
        rationale: str,
        *,
        method: str = "model",
        model_version: str = "",
        decided_by: str = "",
        decided_at: str = "",
    ) -> None:
        """
        One SUPERSEDES edge per ordered pair: new ServiceRecord -> old ServiceRecord.

        Writing the pair again updates the properties and keeps the first created_at,
        so provenance (method, model_version, decided_by, decided_at) is never duplicated.
        """
        if method not in SUPERSEDES_METHODS:
            raise ValueError(f"method must be one of {SUPERSEDES_METHODS}, got {method!r}")
        if self.is_memory:
            self.store.link_record_supersedes(
                new_record_id, old_record_id, scope, confidence, rationale,
                method=method, model_version=model_version,
                decided_by=decided_by, decided_at=decided_at,
            )
            return
        self.store.run_query(
            """
            MATCH (new:ServiceRecord {record_id: $nid}),
                  (old:ServiceRecord {record_id: $oid})
            MERGE (new)-[r:SUPERSEDES]->(old)
            ON CREATE SET r.created_at = $now
            SET r.scope = $scope,
                r.confidence = $confidence,
                r.rationale = $rationale,
                r.method = $method,
                r.model_version = $model_version,
                r.decided_by = $decided_by,
                r.decided_at = $decided_at
            """,
            {
                "nid": new_record_id,
                "oid": old_record_id,
                "scope": scope,
                "confidence": confidence,
                "rationale": rationale,
                "method": method,
                "model_version": model_version,
                "decided_by": decided_by,
                "decided_at": decided_at,
                "now": _now(),
            },
        )

    def unlink_record_supersedes(self, new_record_id: str, old_record_id: str) -> int:
        """Delete the SUPERSEDES edge of one ordered pair; returns 0 or 1."""
        if self.is_memory:
            return self.store.unlink_record_supersedes(new_record_id, old_record_id)
        rows = self.store.run_query(
            """
            MATCH (new:ServiceRecord {record_id: $nid})-[r:SUPERSEDES]->
                  (old:ServiceRecord {record_id: $oid})
            DELETE r
            RETURN count(*) AS deleted
            """,
            {"nid": new_record_id, "oid": old_record_id},
        )
        return int(rows[0]["deleted"]) if rows else 0

    def get_supersedes_link(self, new_record_id: str, old_record_id: str) -> dict | None:
        """The SUPERSEDES link of one ordered pair with its provenance, or None."""
        if self.is_memory:
            return self.store.get_supersedes_link(new_record_id, old_record_id)
        rows = self.store.run_query(
            """
            MATCH (new:ServiceRecord {record_id: $nid})-[r:SUPERSEDES]->
                  (old:ServiceRecord {record_id: $oid})
            RETURN r.scope AS scope, r.confidence AS confidence, r.rationale AS rationale,
                   r.created_at AS created_at, r.method AS method,
                   r.model_version AS model_version, r.decided_by AS decided_by,
                   r.decided_at AS decided_at
            """,
            {"nid": new_record_id, "oid": old_record_id},
        )
        return _link_dict(rows[0]) if rows else None

    def list_supersedes_links(self, old_record_ids: list[str]) -> list[dict]:
        """Every SUPERSEDES link whose old end is in the list, in one query."""
        if not old_record_ids:
            return []
        if self.is_memory:
            return self.store.list_supersedes_links(old_record_ids)
        rows = self.store.run_query(
            """
            MATCH (new:ServiceRecord)-[r:SUPERSEDES]->(old:ServiceRecord)
            WHERE old.record_id IN $oids
            RETURN old.record_id AS old_record_id, new.record_id AS new_record_id,
                   r.scope AS scope, r.confidence AS confidence, r.rationale AS rationale,
                   r.created_at AS created_at, r.method AS method,
                   r.model_version AS model_version, r.decided_by AS decided_by,
                   r.decided_at AS decided_at
            """,
            {"oids": list(old_record_ids)},
        )
        return [
            {"old_record_id": row["old_record_id"], "new_record_id": row["new_record_id"],
             **_link_dict(row)}
            for row in rows
        ]

    def link_record_not_supersedes(
        self, new_record_id: str, old_record_id: str, *, by: str, at: str
    ) -> None:
        """Record that a human rejected this pair; at most one edge per ordered pair."""
        if self.is_memory:
            self.store.link_record_not_supersedes(new_record_id, old_record_id, by=by, at=at)
            return
        self.store.run_query(
            """
            MATCH (new:ServiceRecord {record_id: $nid}),
                  (old:ServiceRecord {record_id: $oid})
            MERGE (new)-[r:NOT_SUPERSEDES]->(old)
            SET r.decided_by = $by,
                r.decided_at = $at
            """,
            {"nid": new_record_id, "oid": old_record_id, "by": by, "at": at},
        )

    def rejected_prior_ids(self, new_record_id: str) -> set[str]:
        """Record IDs a human has said the new record does not supersede."""
        if self.is_memory:
            return self.store.rejected_prior_ids(new_record_id)
        rows = self.store.run_query(
            """
            MATCH (new:ServiceRecord {record_id: $nid})-[:NOT_SUPERSEDES]->(old:ServiceRecord)
            RETURN old.record_id AS record_id
            """,
            {"nid": new_record_id},
        )
        return {row["record_id"] for row in rows}

    def analysis_status(self) -> dict:
        if self.is_memory:
            return self.store.analysis_status()
        rows = self.store.run_query(
            """
            MATCH (sr:ServiceRecord)
            WITH count(sr) AS total,
                 sum(CASE WHEN coalesce(sr.analysis_state,'unscored') = 'unscored' THEN 1 ELSE 0 END) AS unscored,
                 sum(CASE WHEN sr.analysis_state = 'scored' THEN 1 ELSE 0 END) AS scored,
                 sum(CASE WHEN sr.analysis_state = 'needs_review' THEN 1 ELSE 0 END) AS needs_review,
                 sum(CASE WHEN sr.analysis_state = 'reviewed' THEN 1 ELSE 0 END) AS reviewed
            RETURN total, unscored, scored, needs_review, reviewed
            """
        )
        counts = dict(rows[0]) if rows else {"total": 0, "unscored": 0, "scored": 0, "needs_review": 0, "reviewed": 0}
        labels = self.store.run_query(
            """
            MATCH (sr:ServiceRecord)
            WHERE sr.classification_label IS NOT NULL
            RETURN sr.classification_label AS label, count(*) AS count
            ORDER BY label
            """
        )
        counts["by_label"] = {row["label"]: int(row["count"]) for row in labels}
        methods = self.store.run_query(
            """
            MATCH (sr:ServiceRecord)
            WHERE sr.analysis_method IS NOT NULL
            RETURN sr.analysis_method AS method, count(*) AS count
            ORDER BY method
            """
        )
        counts["by_method"] = {row["method"]: int(row["count"]) for row in methods}
        return counts

    def list_corrections_page(self, **filters) -> dict:
        if self.is_memory:
            return self.store.list_corrections_page(**filters)
        params = {
            "limit": int(filters.get("limit", 50)),
            "offset": int(filters.get("offset", 0)),
        }
        where = []
        if filters.get("asset_id"):
            where.append("a.id = $asset_id")
            params["asset_id"] = filters["asset_id"]
        if filters.get("component_changed") is not None:
            where.append("(toLower(coalesce(newer.part_name,'')) <> toLower(coalesce(older.part_name,''))) = $component_changed")
            params["component_changed"] = bool(filters["component_changed"])
        if filters.get("date_from"):
            where.append("newer.occurred_at >= $date_from")
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            where.append("newer.occurred_at <= $date_to")
            params["date_to"] = filters["date_to"]
        where_sql = "WHERE " + " AND ".join(where) if where else ""
        base = f"""
            MATCH (newer:ServiceRecord)-[rel:SUPERSEDES]->(older:ServiceRecord)
            MATCH (newer)-[:ABOUT]->(a:Asset)
            {where_sql}
        """
        summary_rows = self.store.run_query(
            base + """
            RETURN count(*) AS total,
                   sum(CASE WHEN toLower(coalesce(newer.part_name,'')) <> toLower(coalesce(older.part_name,'')) THEN 1 ELSE 0 END) AS changed
            """,
            params,
        )
        total = int(summary_rows[0]["total"]) if summary_rows else 0
        changed = int(summary_rows[0]["changed"] or 0) if summary_rows else 0
        rows = self.store.run_query(
            base + """
            RETURN a.id AS asset_id, a.tail_number AS tail_number,
                   older, newer, rel
            ORDER BY newer.occurred_at DESC, newer.record_id ASC
            SKIP $offset LIMIT $limit
            """,
            params,
        )
        items = []
        for row in rows:
            older = dict(row["older"])
            newer = dict(row["newer"])
            rel = dict(row["rel"])
            items.append({
                "aircraft": {"id": row["asset_id"], "tail_number": row["tail_number"]},
                "older_record": {"id": older.get("record_id"), "part_name": older.get("part_name", ""), "occurred_at": older.get("occurred_at", "")},
                "newer_record": {"id": newer.get("record_id"), "part_name": newer.get("part_name", ""), "occurred_at": newer.get("occurred_at", "")},
                "component_changed": str(older.get("part_name", "")).casefold() != str(newer.get("part_name", "")).casefold(),
                "classification_label": rel.get("scope") or newer.get("classification_label"),
                "classification": rel.get("scope") or newer.get("classification_label"),
                "score": rel.get("confidence", newer.get("confidence")),
                "rationale": rel.get("rationale", newer.get("classification_rationale", "")),
                "review_status": newer.get("analysis_state", "scored"),
            })
        offset = params["offset"]
        next_offset = offset + len(items) if offset + len(items) < total else None
        return {
            "items": items, "total": total, "next": next_offset,
            "summary": {
                "total_corrections": total,
                "component_changed": changed,
                "component_changed_pct": round(changed * 100 / total, 1) if total else 0.0,
            },
        }

    def update_service_record(self, record_id: str, updates: dict) -> dict | None:
        """Apply a partial update to a ServiceRecord.  Returns the updated node."""
        updates = {**updates, "updated_at": _now()}
        if self.is_memory:
            return self.store.update_service_record(record_id, updates)
        rows = self.store.run_query(
            """
            MATCH (sr:ServiceRecord {record_id: $rid})
            SET sr += $updates
            RETURN sr
            """,
            {"rid": record_id, "updates": updates},
        )
        return dict(rows[0]["sr"]) if rows else None


