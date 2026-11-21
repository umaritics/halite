

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
        """SUPERSEDES edge: new ServiceRecord → old ServiceRecord."""
        new_id = self._service_record_ids.get(new_record_id)
        old_id = self._service_record_ids.get(old_record_id)
        if not new_id or not old_id:
            return
        self._add_edge(
            new_id,
            old_id,
            "SUPERSEDES",
            {"scope": scope, "confidence": confidence, "rationale": rationale},
        )

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


