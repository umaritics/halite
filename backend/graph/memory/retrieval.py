

class RetrievalMixin:
    """Retrieval graph operations; preserved from the pre-split implementation."""

    def get_neighborhood(self, node_id: str) -> dict:
        node = self._get_node(node_id)
        if not node:
            return {}
        return {"node": node, "neighbors": self._neighbors(node_id)}

    def graph_overview(self, limit: int = 200) -> dict:
        nodes = list(self.nodes.values())[:limit]
        node_ids = {n["id"] for n in nodes}
        edges = [
            {
                "source": e["source"],
                "target": e["target"],
                "type": e["type"],
                "properties": e.get("properties", {}),
            }
            for e in self.edges
            if e["source"] in node_ids and e["target"] in node_ids
        ]
        return {"nodes": nodes, "edges": edges}

    def list_asset_history_recent(self, asset_id: str, limit: int = 30) -> list[dict]:
        """Newest-first ServiceRecords linked to asset_id (includes corrected_by)."""
        records = self.list_asset_history(asset_id, limit=10_000)
        records.sort(key=lambda r: r.get("occurred_at", ""), reverse=True)
        return records[:limit]

    def get_service_records_by_ids(self, record_ids: list[str]) -> list[dict]:
        """Batch fetch ServiceRecords by record_id."""
        wanted = set(record_ids)
        out = []
        for node in self._find_nodes("ServiceRecord"):
            rid = node.get("record_id") or node.get("id")
            if rid in wanted:
                out.append(node)
        return out

    def list_service_records(
        self,
        status: str | None = None,
        asset_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """List ServiceRecords optionally filtered by status and asset_id."""
        records = self._find_nodes("ServiceRecord")
        if status:
            records = [r for r in records if r.get("status") == status]
        if asset_id:
            # Keep only records linked to this asset
            linked_record_ids: set[str] = set()
            for edge in self.edges:
                if edge["target"] == asset_id and edge["type"] == "ABOUT":
                    linked_record_ids.add(edge["source"])
            records = [r for r in records if r["id"] in linked_record_ids]
        records.sort(key=lambda r: r.get("occurred_at", ""), reverse=True)
        if limit is not None:
            records = records[: int(limit)]
        return records


