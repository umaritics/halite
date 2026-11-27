import uuid
from copy import deepcopy
from ._helpers import _now

from .retrieval import RetrievalMixin
from .integrity import IntegrityMixin
from .legacy import LegacyMixin


class MemoryGraphStore(RetrievalMixin, IntegrityMixin, LegacyMixin):
    """Compatible graph facade; vertical methods live in dedicated mixins."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self._service_record_ids: dict[str, str] = {}
        self._asset_tail_ids: dict[str, str] = {}

    def close(self):
        pass

    def init_schema(self):
        pass

    def _add_node(self, label: str, props: dict) -> dict:
        node_id = props.get("id") or str(uuid.uuid4())
        props = {**props, "id": node_id, "label": label}
        if "created_at" not in props:
            props["created_at"] = _now()
        if "updated_at" not in props:
            props["updated_at"] = _now()
        self.nodes[node_id] = props
        if label == "ServiceRecord" and props.get("record_id"):
            self._service_record_ids[props["record_id"]] = node_id
        elif label == "Asset" and props.get("tail_number"):
            self._asset_tail_ids[props["tail_number"]] = node_id
        return deepcopy(props)

    def _get_node(self, node_id: str) -> dict | None:
        node = self.nodes.get(node_id)
        return deepcopy(node) if node else None

    def _find_nodes(self, label: str | None = None, **filters) -> list[dict]:
        results = []
        for node in self.nodes.values():
            if label and node.get("label") != label:
                continue
            match = all(node.get(k) == v for k, v in filters.items())
            if match:
                results.append(deepcopy(node))
        return results

    def _update_node(self, node_id: str, updates: dict) -> dict | None:
        if node_id not in self.nodes:
            return None
        self.nodes[node_id].update(updates)
        self.nodes[node_id]["updated_at"] = _now()
        return deepcopy(self.nodes[node_id])

    def _delete_node(self, node_id: str) -> bool:
        if node_id not in self.nodes:
            return False
        node = self.nodes[node_id]
        if node.get("label") == "ServiceRecord":
            self._service_record_ids.pop(node.get("record_id"), None)
        elif node.get("label") == "Asset":
            self._asset_tail_ids.pop(node.get("tail_number"), None)
        del self.nodes[node_id]
        self.edges = [e for e in self.edges if e["source"] != node_id and e["target"] != node_id]
        return True

    def _add_edge(self, source: str, target: str, rel_type: str, props: dict | None = None):
        self.edges.append(
            {
                "source": source,
                "target": target,
                "type": rel_type,
                "properties": props or {},
            }
        )

    def _neighbors(self, node_id: str) -> list[dict]:
        neighbors = []
        for edge in self.edges:
            if edge["source"] == node_id:
                target = self._get_node(edge["target"])
                if target:
                    neighbors.append({"node": target, "relationship": edge["type"], "direction": "out"})
            elif edge["target"] == node_id:
                source = self._get_node(edge["source"])
                if source:
                    neighbors.append({"node": source, "relationship": edge["type"], "direction": "in"})
        return neighbors

    def run_query(self, query: str, parameters: dict | None = None):
        raise NotImplementedError("Memory store uses explicit methods, not Cypher")

    def find_or_create_asset(self, tail_number: str, metadata: dict) -> dict:
        """Return existing Asset by tail_number, or create one."""
        existing_id = self._asset_tail_ids.get(tail_number)
        if existing_id:
            return self._get_node(existing_id)
        props = {
            "tail_number": tail_number,
            "make": metadata.get("make", ""),
            "model": metadata.get("model", ""),
            "serial_number": metadata.get("serial_number", ""),
        }
        return self._add_node("Asset", props)

    def create_service_record(self, data: dict) -> dict:
        """Create a ServiceRecord.  Idempotent on record_id."""
        existing_id = self._service_record_ids.get(data["record_id"])
        if existing_id:
            return self._get_node(existing_id)
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
            "confidence": data.get("confidence"),
            "source": data.get("source", "faa_sdr"),
        }
        for key in (
            "analysis_state", "legacy_confidence", "scored_at", "analysed_at",
            "classification_label", "classification_rationale", "candidate_count",
            "candidates_considered", "analysis_model", "analysis_method",
            "analysis_passes", "analysis_vote_agreement", "analysis_votes_json",
            "analysis_prompt_tokens", "analysis_completion_tokens",
            "analysis_reasoning_tokens", "analysis_total_tokens", "history_size",
            "review_note",
        ):
            if key in data:
                props[key] = data[key]
        for key in (
            "legacy_confidence", "scored_at", "classification_label",
            "classification_rationale", "candidate_count",
            "candidates_considered", "analysis_model", "history_size",
            "review_note",
        ):
            if key in data:
                props[key] = data[key]
        if data.get("id"):
            props["id"] = data["id"]
        return self._add_node("ServiceRecord", props)

    def get_service_record(self, record_id: str) -> dict | None:
        """Return ServiceRecord by record_id, or None."""
        node_id = self._service_record_ids.get(record_id)
        return self._get_node(node_id) if node_id else None

    def link_record_about_asset(self, record_id: str, asset_id: str) -> None:
        """ABOUT edge: ServiceRecord node_id → Asset node_id."""
        # Find the ServiceRecord node's internal id
        source_id = self._service_record_ids.get(record_id)
        if not source_id:
            return
        if any(
            edge["source"] == source_id
            and edge["target"] == asset_id
            and edge["type"] == "ABOUT"
            for edge in self.edges
        ):
            return
        self._add_edge(source_id, asset_id, "ABOUT")

    def count_service_records(self) -> int:
        """Count ServiceRecord nodes without materializing record dictionaries."""
        return sum(1 for node in self.nodes.values() if node.get("label") == "ServiceRecord")

    def list_assets_with_counts(self) -> list[dict]:
        """Return assets and record counts with one pass over ABOUT edges."""
        assets = self._find_nodes("Asset")
        counts = {asset["id"]: 0 for asset in assets}
        for edge in self.edges:
            if edge["type"] == "ABOUT" and edge["target"] in counts:
                counts[edge["target"]] += 1

        result = [
            {**asset, "record_count": counts[asset["id"]]}
            for asset in assets
        ]
        result.sort(key=lambda asset: asset.get("tail_number", ""))
        return result

    def list_asset_history(self, asset_id: str, limit: int = 50) -> list[dict]:
        """Return ServiceRecords linked to asset_id, ascending by occurred_at."""
        records = []
        corrected_by = {}
        for edge in self.edges:
            if edge["target"] == asset_id and edge["type"] == "ABOUT":
                node = self._get_node(edge["source"])
                if node and node.get("label") == "ServiceRecord":
                    records.append(node)
            elif edge["type"] == "SUPERSEDES":
                newer = self.nodes.get(edge["source"])
                if newer:
                    corrected_by[edge["target"]] = {
                        "record_id": newer.get("record_id"),
                        "part_name": newer.get("part_name", ""),
                    }
        records.sort(key=lambda r: r.get("occurred_at", ""))
        asset = self._get_node(asset_id)
        result = []
        for record in records[:limit]:
            view = dict(record)
            view["classification"] = record.get("classification_label")
            if asset:
                view["asset_id"] = asset_id
                view["tail_number"] = asset.get("tail_number", "")
            if record["id"] in corrected_by:
                view["corrected_by"] = corrected_by[record["id"]]
            result.append(view)
        return result

    def _maintenance_record_view(self, record: dict) -> dict:
        """Return a ServiceRecord enriched with its asset and correction link."""
        view = dict(record)
        view["classification"] = record.get("classification_label")
        asset = None
        for edge in self.edges:
            if edge["source"] == record["id"] and edge["type"] == "ABOUT":
                asset = self._get_node(edge["target"])
                break
        if asset:
            view["asset_id"] = asset["id"]
            view["tail_number"] = asset.get("tail_number", "")
        for edge in self.edges:
            if edge["target"] == record["id"] and edge["type"] == "SUPERSEDES":
                newer = self._get_node(edge["source"])
                if newer:
                    view["corrected_by"] = {
                        "record_id": newer.get("record_id"),
                        "part_name": newer.get("part_name", ""),
                    }
                    break
        return view

    def list_service_records_page(
        self,
        *,
        asset_id: str | None = None,
        q: str | None = None,
        status: str | None = None,
        analysis_state: str | None = None,
        part: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "occurred_at_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        assets_by_record = {}
        corrected_by = {}
        for edge in self.edges:
            if edge["type"] == "ABOUT":
                assets_by_record[edge["source"]] = self.nodes.get(edge["target"])
            elif edge["type"] == "SUPERSEDES":
                newer = self.nodes.get(edge["source"])
                if newer:
                    corrected_by[edge["target"]] = {
                        "record_id": newer.get("record_id"),
                        "part_name": newer.get("part_name", ""),
                    }
        records = []
        for record in self._find_nodes("ServiceRecord"):
            view = dict(record)
            view["classification"] = record.get("classification_label")
            asset = assets_by_record.get(record["id"])
            if asset:
                view["asset_id"] = asset["id"]
                view["tail_number"] = asset.get("tail_number", "")
            if record["id"] in corrected_by:
                view["corrected_by"] = corrected_by[record["id"]]
            records.append(view)
        if asset_id:
            records = [r for r in records if r.get("asset_id") == asset_id]
        if q:
            needle = q.casefold()
            records = [
                r for r in records
                if needle in " ".join(str(r.get(k, "")) for k in (
                    "record_id", "text", "part_name", "part_condition",
                    "part_location", "tail_number",
                )).casefold()
            ]
        if status:
            records = [r for r in records if r.get("status") == status]
        if analysis_state:
            records = [r for r in records if r.get("analysis_state", "unscored") == analysis_state]
        if part:
            records = [r for r in records if part.casefold() in str(r.get("part_name", "")).casefold()]
        if date_from:
            records = [r for r in records if str(r.get("occurred_at", "")) >= date_from]
        if date_to:
            records = [r for r in records if str(r.get("occurred_at", "")) <= date_to]
        if sort.startswith("record_id"):
            records.sort(
                key=lambda r: str(r.get("record_id", "")),
                reverse=sort == "record_id_desc",
            )
        else:
            # Stable secondary key is always record_id ascending.
            records.sort(key=lambda r: str(r.get("record_id", "")))
            records.sort(
                key=lambda r: str(r.get("occurred_at", "")),
                reverse=sort == "occurred_at_desc",
            )
        total = len(records)
        items = records[offset:offset + limit]
        next_offset = offset + len(items) if offset + len(items) < total else None
        return {"items": items, "total": total, "next": next_offset}


