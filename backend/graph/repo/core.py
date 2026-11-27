import json
import logging
import uuid
from ._helpers import _now

from .retrieval import RetrievalMixin
from .integrity import IntegrityMixin
from .legacy import LegacyMixin


logger = logging.getLogger(__name__)


class GraphRepository(RetrievalMixin, IntegrityMixin, LegacyMixin):
    """Compatible graph facade; vertical methods live in dedicated mixins."""

    def __init__(self, store):
        self.store = store
        self.is_memory = hasattr(store, "nodes")

    def init_schema(self):
        self.store.init_schema()

    def parse_json_safe(self, text: str) -> dict | list:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM response")
            return {}

    def find_or_create_asset(self, tail_number: str, metadata: dict | None = None) -> dict:
        """
        Return an existing Asset by tail_number, or create one.

        metadata may contain: make, model, serial_number.
        """
        metadata = metadata or {}
        if self.is_memory:
            return self.store.find_or_create_asset(tail_number, metadata)
        rows = self.store.run_query(
            "MATCH (a:Asset {tail_number: $tail}) RETURN a",
            {"tail": tail_number},
        )
        if rows:
            return dict(rows[0]["a"])
        asset_id = str(uuid.uuid4())
        props = {
            "id": asset_id,
            "tail_number": tail_number,
            "make": metadata.get("make", ""),
            "model": metadata.get("model", ""),
            "serial_number": metadata.get("serial_number", ""),
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.store.run_query(
            "CREATE (a:Asset) SET a = $props RETURN a",
            {"props": props},
        )
        return props

    def create_service_record(self, data: dict) -> dict:
        """
        Create a ServiceRecord node.  Idempotent: if record_id already exists,
        return the existing node without modification.

        Required keys in data: record_id, asset_key, occurred_at, text.
        Optional:  submitted_at, part_name, part_condition, part_location,
                   jasc_code, status, confidence, source, created_at.
        """
        if self.is_memory:
            return self.store.create_service_record(data)
        # Idempotency check
        rows = self.store.run_query(
            "MATCH (sr:ServiceRecord {record_id: $rid}) RETURN sr",
            {"rid": data["record_id"]},
        )
        if rows:
            return dict(rows[0]["sr"])
        props = {
            "record_id": data["record_id"],
            "asset_key": data.get("asset_key", ""),
            "occurred_at": data.get("occurred_at", ""),
            "submitted_at": data.get("submitted_at", ""),
            "part_name": data.get("part_name", ""),
            "part_condition": data.get("part_condition", ""),
            "part_location": data.get("part_location", ""),
            "stage_of_operation": data.get("stage_of_operation", ""),
            "how_discovered": data.get("how_discovered", ""),
            "nature_of_condition": data.get("nature_of_condition", ""),
            "precautionary_procedure": data.get("precautionary_procedure", ""),
            "jasc_code": data.get("jasc_code", ""),
            "text": data.get("text", ""),
            "status": data.get("status", "unscored"),
            "analysis_state": data.get("analysis_state", "unscored"),
            "confidence": data.get("confidence", None),
            "source": data.get("source", "faa_sdr"),
            "id": data.get("id") or str(uuid.uuid4()),
            "created_at": data.get("created_at") or _now(),
            "updated_at": _now(),
        }
        for key in (
            "legacy_confidence", "scored_at", "classification_label",
            "classification_rationale", "candidate_count",
            "candidates_considered", "analysis_model", "history_size",
            "review_note", "analysed_at", "analysis_method", "analysis_passes",
            "analysis_vote_agreement", "analysis_votes_json",
            "analysis_prompt_tokens", "analysis_completion_tokens",
            "analysis_reasoning_tokens", "analysis_total_tokens",
        ):
            if key in data:
                props[key] = data[key]
        self.store.run_query(
            "CREATE (sr:ServiceRecord) SET sr = $props RETURN sr",
            {"props": props},
        )
        return props

    def get_service_record(self, record_id: str) -> dict | None:
        """Return a ServiceRecord by record_id, or None."""
        if self.is_memory:
            return self.store.get_service_record(record_id)
        rows = self.store.run_query(
            "MATCH (sr:ServiceRecord {record_id: $rid}) RETURN sr",
            {"rid": record_id},
        )
        return dict(rows[0]["sr"]) if rows else None

    def link_record_about_asset(self, record_id: str, asset_id: str) -> None:
        """Create ABOUT edge: ServiceRecord → Asset."""
        if self.is_memory:
            self.store.link_record_about_asset(record_id, asset_id)
            return
        self.store.run_query(
            """
            MATCH (sr:ServiceRecord {record_id: $rid}), (a:Asset {id: $aid})
            MERGE (sr)-[:ABOUT]->(a)
            """,
            {"rid": record_id, "aid": asset_id},
        )

    def count_service_records(self) -> int:
        """Count ServiceRecord nodes without loading their properties into Python."""
        if self.is_memory:
            return self.store.count_service_records()
        rows = self.store.run_query(
            "MATCH (sr:ServiceRecord) RETURN count(sr) AS record_count"
        )
        return int(rows[0]["record_count"]) if rows else 0

    def list_assets_with_counts(self) -> list[dict]:
        """Return every Asset with its ServiceRecord count in one graph query."""
        if self.is_memory:
            return self.store.list_assets_with_counts()
        rows = self.store.run_query(
            """
            MATCH (a:Asset)
            OPTIONAL MATCH (sr:ServiceRecord)-[:ABOUT]->(a)
            RETURN a, count(sr) AS record_count
            ORDER BY a.tail_number
            """
        )
        return [
            {**dict(row["a"]), "record_count": int(row["record_count"])}
            for row in rows
        ]

    def list_asset_history(self, asset_id: str, limit: int = 50) -> list[dict]:
        """Return ServiceRecords for an asset ordered ascending by occurred_at."""
        if self.is_memory:
            return self.store.list_asset_history(asset_id, limit)
        rows = self.store.run_query(
            """
            MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset {id: $aid})
            OPTIONAL MATCH (corrector:ServiceRecord)-[:SUPERSEDES]->(sr)
            RETURN sr, a.tail_number AS tail_number,
                   head(collect(CASE WHEN corrector IS NULL THEN null ELSE {record_id: corrector.record_id, part_name: corrector.part_name} END)) AS corrected_by
            ORDER BY sr.occurred_at ASC
            LIMIT $limit
            """,
            {"aid": asset_id, "limit": limit},
        )
        result = []
        for row in rows:
            record = {
                **dict(row["sr"]),
                "asset_id": asset_id,
                "tail_number": row["tail_number"],
            }
            record["classification"] = record.get("classification_label")
            if row.get("corrected_by"):
                record["corrected_by"] = dict(row["corrected_by"])
            result.append(record)
        return result

    def list_service_records_page(self, **filters) -> dict:
        """Filter, sort and paginate fleet records in the backing store."""
        if self.is_memory:
            return self.store.list_service_records_page(**filters)
        asset_id = filters.get("asset_id")
        q = filters.get("q")
        status = filters.get("status")
        analysis_state = filters.get("analysis_state")
        part = filters.get("part")
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        sort = filters.get("sort", "occurred_at_desc")
        limit = int(filters.get("limit", 50))
        offset = int(filters.get("offset", 0))
        params = {"limit": limit, "offset": offset}
        where = []
        if asset_id:
            where.append("a.id = $asset_id")
            params["asset_id"] = asset_id
        if q:
            where.append("toLower(coalesce(sr.record_id,'') + ' ' + coalesce(sr.text,'') + ' ' + coalesce(sr.part_name,'') + ' ' + coalesce(sr.part_condition,'') + ' ' + coalesce(sr.part_location,'') + ' ' + coalesce(a.tail_number,'')) CONTAINS toLower($q)")
            params["q"] = q
        if status:
            where.append("sr.status = $status")
            params["status"] = status
        if analysis_state:
            where.append("coalesce(sr.analysis_state, 'unscored') = $analysis_state")
            params["analysis_state"] = analysis_state
        if part:
            where.append("toLower(coalesce(sr.part_name,'')) CONTAINS toLower($part)")
            params["part"] = part
        if date_from:
            where.append("sr.occurred_at >= $date_from")
            params["date_from"] = date_from
        if date_to:
            where.append("sr.occurred_at <= $date_to")
            params["date_to"] = date_to
        where_sql = "WHERE " + " AND ".join(where) if where else ""
        order_sql = {
            "occurred_at_desc": "sr.occurred_at DESC, sr.record_id ASC",
            "occurred_at_asc": "sr.occurred_at ASC, sr.record_id ASC",
            "record_id_asc": "sr.record_id ASC",
            "record_id_desc": "sr.record_id DESC",
        }.get(sort, "sr.occurred_at DESC, sr.record_id ASC")
        count_rows = self.store.run_query(
            f"""
            MATCH (sr:ServiceRecord)
            OPTIONAL MATCH (sr)-[:ABOUT]->(a:Asset)
            WITH sr, a
            {where_sql}
            RETURN count(sr) AS total
            """,
            params,
        )
        total = int(count_rows[0]["total"]) if count_rows else 0
        rows = self.store.run_query(
            f"""
            MATCH (sr:ServiceRecord)
            OPTIONAL MATCH (sr)-[:ABOUT]->(a:Asset)
            WITH sr, a
            {where_sql}
            OPTIONAL MATCH (corrector:ServiceRecord)-[:SUPERSEDES]->(sr)
            WITH sr, a, head(collect(CASE WHEN corrector IS NULL THEN null ELSE {{record_id: corrector.record_id, part_name: corrector.part_name}} END)) AS corrected_by
            RETURN sr, a.id AS asset_id, a.tail_number AS tail_number, corrected_by
            ORDER BY {order_sql}
            SKIP $offset LIMIT $limit
            """,
            params,
        )
        items = []
        for row in rows:
            item = {**dict(row["sr"]), "asset_id": row["asset_id"], "tail_number": row["tail_number"]}
            item["classification"] = item.get("classification_label")
            if row.get("corrected_by"):
                item["corrected_by"] = dict(row["corrected_by"])
            items.append(item)
        next_offset = offset + len(items) if offset + len(items) < total else None
        return {"items": items, "total": total, "next": next_offset}


