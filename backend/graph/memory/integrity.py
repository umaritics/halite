from ._helpers import _now


class IntegrityMixin:
    """Integrity graph operations; preserved from the pre-split implementation."""

    def _link_edge(self, rel_type: str, new_record_id: str, old_record_id: str) -> dict | None:
        new_id = self._service_record_ids.get(new_record_id)
        old_id = self._service_record_ids.get(old_record_id)
        if not new_id or not old_id:
            return None
        for edge in self.edges:
            if edge["type"] == rel_type and edge["source"] == new_id and edge["target"] == old_id:
                return edge
        return None

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
        """SUPERSEDES edge: new -> old. One per ordered pair; a repeat keeps the first created_at."""
        new_id = self._service_record_ids.get(new_record_id)
        old_id = self._service_record_ids.get(old_record_id)
        if not new_id or not old_id:
            return
        edge = self._link_edge("SUPERSEDES", new_record_id, old_record_id)
        if edge is None:
            self._add_edge(new_id, old_id, "SUPERSEDES", {"created_at": _now()})
            edge = self.edges[-1]
        edge["properties"].update({
            "scope": scope, "confidence": confidence, "rationale": rationale,
            "method": method, "model_version": model_version,
            "decided_by": decided_by, "decided_at": decided_at,
        })

    def unlink_record_supersedes(self, new_record_id: str, old_record_id: str) -> int:
        edge = self._link_edge("SUPERSEDES", new_record_id, old_record_id)
        if edge is None:
            return 0
        self.edges.remove(edge)
        return 1

    @staticmethod
    def _supersedes_view(props: dict) -> dict:
        return {
            "scope": props.get("scope"),
            "confidence": props.get("confidence"),
            "rationale": props.get("rationale"),
            "created_at": props.get("created_at"),
            "method": props.get("method") or "model",
            "model_version": props.get("model_version") or "",
            "decided_by": props.get("decided_by") or "",
            "decided_at": props.get("decided_at") or "",
        }

    def get_supersedes_link(self, new_record_id: str, old_record_id: str) -> dict | None:
        edge = self._link_edge("SUPERSEDES", new_record_id, old_record_id)
        return self._supersedes_view(edge["properties"]) if edge else None

    def list_supersedes_links(self, old_record_ids: list[str]) -> list[dict]:
        wanted = set(old_record_ids)
        links = []
        for edge in self.edges:
            if edge["type"] != "SUPERSEDES":
                continue
            new = self._get_node(edge["source"])
            old = self._get_node(edge["target"])
            if new and old and old.get("record_id") in wanted:
                links.append({
                    "old_record_id": old["record_id"],
                    "new_record_id": new["record_id"],
                    **self._supersedes_view(edge["properties"]),
                })
        return links

    def link_record_not_supersedes(
        self, new_record_id: str, old_record_id: str, *, by: str, at: str
    ) -> None:
        """NOT_SUPERSEDES edge: a human rejected this pair. One per ordered pair."""
        new_id = self._service_record_ids.get(new_record_id)
        old_id = self._service_record_ids.get(old_record_id)
        if not new_id or not old_id:
            return
        edge = self._link_edge("NOT_SUPERSEDES", new_record_id, old_record_id)
        if edge is None:
            self._add_edge(new_id, old_id, "NOT_SUPERSEDES")
            edge = self.edges[-1]
        edge["properties"].update({"decided_by": by, "decided_at": at})

    def rejected_prior_ids(self, new_record_id: str) -> set[str]:
        new_id = self._service_record_ids.get(new_record_id)
        rejected = set()
        for edge in self.edges:
            if edge["type"] == "NOT_SUPERSEDES" and edge["source"] == new_id:
                old = self._get_node(edge["target"])
                if old:
                    rejected.add(old["record_id"])
        return rejected

    def analysis_status(self) -> dict:
        records = self._find_nodes("ServiceRecord")
        states = {"unscored": 0, "scored": 0, "needs_review": 0, "reviewed": 0}
        by_label: dict[str, int] = {}
        by_method: dict[str, int] = {}
        for record in records:
            state = record.get("analysis_state") or "unscored"
            states[state] = states.get(state, 0) + 1
            label = record.get("classification_label")
            if label:
                by_label[label] = by_label.get(label, 0) + 1
            method = record.get("analysis_method")
            if method:
                by_method[method] = by_method.get(method, 0) + 1
        return {
            "total": len(records), **states,
            "by_label": dict(sorted(by_label.items())),
            "by_method": dict(sorted(by_method.items())),
        }

    def list_corrections_page(
        self,
        *,
        asset_id: str | None = None,
        component_changed: bool | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        rows = []
        for edge in self.edges:
            if edge["type"] != "SUPERSEDES":
                continue
            newer = self._get_node(edge["source"])
            older = self._get_node(edge["target"])
            if not newer or not older:
                continue
            newer_view = self._maintenance_record_view(newer)
            changed = str(newer.get("part_name", "")).casefold() != str(older.get("part_name", "")).casefold()
            if asset_id and newer_view.get("asset_id") != asset_id:
                continue
            occurred = str(newer.get("occurred_at", ""))
            if date_from and occurred < date_from:
                continue
            if date_to and occurred > date_to:
                continue
            if component_changed is not None and changed is not component_changed:
                continue
            props = edge.get("properties", {})
            rows.append({
                "aircraft": {"id": newer_view.get("asset_id"), "tail_number": newer_view.get("tail_number")},
                "older_record": {"id": older.get("record_id"), "part_name": older.get("part_name", ""), "occurred_at": older.get("occurred_at", "")},
                "newer_record": {"id": newer.get("record_id"), "part_name": newer.get("part_name", ""), "occurred_at": newer.get("occurred_at", "")},
                "component_changed": changed,
                "classification_label": props.get("scope") or newer.get("classification_label"),
                "classification": props.get("scope") or newer.get("classification_label"),
                "score": props.get("confidence", newer.get("confidence")),
                "rationale": props.get("rationale", newer.get("classification_rationale", "")),
                "review_status": newer.get("analysis_state", "scored"),
            })
        rows.sort(key=lambda row: (row["newer_record"]["occurred_at"], row["newer_record"]["id"]), reverse=True)
        total_all = len(rows)
        changed_count = sum(1 for row in rows if row["component_changed"])
        items = rows[offset:offset + limit]
        next_offset = offset + len(items) if offset + len(items) < total_all else None
        return {
            "items": items,
            "total": total_all,
            "next": next_offset,
            "summary": {
                "total_corrections": total_all,
                "component_changed": changed_count,
                "component_changed_pct": round(changed_count * 100 / total_all, 1) if total_all else 0.0,
            },
        }

    def update_service_record(self, record_id: str, updates: dict) -> dict | None:
        """Apply partial update to a ServiceRecord identified by record_id."""
        node_id = self._service_record_ids.get(record_id)
        if not node_id:
            return None
        return self._update_node(node_id, updates)


