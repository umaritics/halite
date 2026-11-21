import logging
from ._helpers import _now

logger = logging.getLogger(__name__)


class IntegrityMixin:
    """Integrity graph operations; preserved from the pre-split implementation."""

    def link_record_supersedes(
        self,
        new_record_id: str,
        old_record_id: str,
        scope: str,
        confidence: float,
        rationale: str,
    ) -> None:
        """
        Create SUPERSEDES edge: new ServiceRecord → old ServiceRecord.

        Properties: scope, confidence, rationale, created_at.
        """
        if self.is_memory:
            self.store.link_record_supersedes(
                new_record_id, old_record_id, scope, confidence, rationale
            )
            return
        self.store.run_query(
            """
            MATCH (new:ServiceRecord {record_id: $nid}),
                  (old:ServiceRecord {record_id: $oid})
            MERGE (new)-[r:SUPERSEDES]->(old)
            SET r.scope = $scope,
                r.confidence = $confidence,
                r.rationale = $rationale,
                r.created_at = $now
            """,
            {
                "nid": new_record_id,
                "oid": old_record_id,
                "scope": scope,
                "confidence": confidence,
                "rationale": rationale,
                "now": _now(),
            },
        )

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


