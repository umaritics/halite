import uuid
from copy import deepcopy
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryGraphStore:
    """In-memory graph for demo mode when Neo4j is not configured."""

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

    # --- Public graph operations used by routes/agents ---

    def run_query(self, query: str, parameters: dict | None = None):
        raise NotImplementedError("Memory store uses explicit methods, not Cypher")

    def create_component(self, data: dict) -> dict:
        existing = self._find_nodes("Component", file_path=data.get("file_path", ""))
        if existing and data.get("file_path"):
            return self._update_node(existing[0]["id"], data)
        return self._add_node("Component", data)

    def create_decision(self, data: dict) -> dict:
        return self._add_node("Decision", data)

    def create_commit(self, data: dict) -> dict:
        existing = self._find_nodes("Commit", id=data["id"])
        if existing:
            return existing[0]
        return self._add_node("Commit", data)

    def create_ticket(self, data: dict) -> dict:
        existing = self._find_nodes("Ticket", id=data["id"])
        if existing:
            return existing[0]
        return self._add_node("Ticket", data)

    def create_document(self, data: dict) -> dict:
        return self._add_node("Document", data)

    def list_decisions(self, status: str | None = None) -> list[dict]:
        decisions = self._find_nodes("Decision")
        if status:
            decisions = [d for d in decisions if d.get("status") == status]
        enriched = []
        for d in decisions:
            full = self._decision_with_context(d["id"])
            full["component_names"] = [c.get("name") for c in full.get("components") or [] if c.get("name")]
            enriched.append(full)
        return sorted(enriched, key=lambda d: d.get("created_at", ""), reverse=True)

    def get_decision(self, decision_id: str) -> dict | None:
        node = self._get_node(decision_id)
        if not node or node.get("label") != "Decision":
            return None
        return self._decision_with_context(decision_id)

    def _decision_with_context(self, decision_id: str) -> dict:
        decision = self._get_node(decision_id)
        components = []
        tickets = []
        for n in self._neighbors(decision_id):
            node = n["node"]
            if node["label"] == "Component" and n["relationship"] == "ABOUT" and n["direction"] == "out":
                components.append(node)
            if node["label"] == "Ticket" and n["relationship"] == "REFERENCED_IN" and n["direction"] == "out":
                tickets.append(node)
        return {**decision, "components": components, "tickets": tickets}

    def update_decision(self, decision_id: str, updates: dict) -> dict | None:
        node = self._get_node(decision_id)
        if not node or node.get("label") != "Decision":
            return None
        return self._update_node(decision_id, updates)

    def delete_decision(self, decision_id: str) -> bool:
        node = self._get_node(decision_id)
        if not node or node.get("label") != "Decision":
            return False
        return self._delete_node(decision_id)

    def link_decision_about(self, decision_id: str, component_id: str, confidence: float = 1.0):
        self._add_edge(decision_id, component_id, "ABOUT", {"confidence": confidence})

    def link_decision_ticket(self, decision_id: str, ticket_id: str):
        self._add_edge(decision_id, ticket_id, "REFERENCED_IN")

    def link_decision_document(self, decision_id: str, document_id: str):
        self._add_edge(decision_id, document_id, "EXTRACTED_FROM")

    def link_component_depends(self, source_id: str, target_id: str, description: str = ""):
        self._add_edge(source_id, target_id, "DEPENDS_ON", {"description": description})

    def link_commit_modified(self, commit_id: str, component_id: str):
        self._add_edge(commit_id, component_id, "MODIFIED")

    def link_commit_may_invalidate(self, commit_id: str, decision_id: str, reason: str):
        self._add_edge(commit_id, decision_id, "MAY_INVALIDATE", {"reason": reason})

    def link_ticket_relates(self, ticket_id: str, component_id: str):
        self._add_edge(ticket_id, component_id, "RELATES_TO")

    def find_component_by_name(self, name: str) -> dict | None:
        name_lower = name.lower()
        for node in self._find_nodes("Component"):
            if name_lower in node.get("name", "").lower():
                return node
        return None

    def find_component_by_path(self, file_path: str) -> dict | None:
        for node in self._find_nodes("Component"):
            if node.get("file_path") == file_path:
                return node
        return None

    def list_components(self) -> list[dict]:
        return self._find_nodes("Component")

    def list_tickets(self) -> list[dict]:
        return self._find_nodes("Ticket")

    def search_entities(self, entities: list[str]) -> tuple[list[dict], list[dict]]:
        components = []
        decisions = []
        seen_c, seen_d = set(), set()
        for entity in entities[:15]:
            el = entity.lower().strip()
            if len(el) < 2:
                continue
            for node in self._find_nodes("Component"):
                if node["id"] in seen_c:
                    continue
                if el in node.get("name", "").lower() or el in (node.get("file_path") or "").lower():
                    components.append(node)
                    seen_c.add(node["id"])
            for node in self._find_nodes("Decision"):
                if node["id"] in seen_d:
                    continue
                if el in node.get("title", "").lower() or el in (node.get("reasoning") or "").lower():
                    full = self._decision_with_context(node["id"])
                    decisions.append(full)
                    seen_d.add(node["id"])
        return components[:20], decisions[:20]

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

    def get_alerts(self) -> list[dict]:
        alerts = []
        for decision in self._find_nodes("Decision", status="needs_review"):
            commit = None
            component = None
            for n in self._neighbors(decision["id"]):
                if n["node"]["label"] == "Commit" and n["relationship"] == "MAY_INVALIDATE":
                    commit = n["node"]
                if n["node"]["label"] == "Component" and n["relationship"] == "ABOUT" and n["direction"] == "in":
                    component = n["node"]
            alerts.append(
                {
                    "decision": decision,
                    "commit": commit,
                    "component": component,
                    "flagged_at": decision.get("updated_at")
                    or (commit.get("timestamp") if commit else None)
                    or decision.get("created_at"),
                }
            )
        return alerts

    def seed_demo_data(self):
        if self.nodes:
            return

        auth = self.create_component(
            {
                "name": "AuthModule",
                "type": "module",
                "file_path": "src/auth/auth.service.ts",
                "description": "Handles JWT authentication and token validation for API requests.",
                "language": "typescript",
            }
        )
        api = self.create_component(
            {
                "name": "ApiGateway",
                "type": "service",
                "file_path": "src/api/gateway.ts",
                "description": "Central API gateway routing requests to internal services.",
                "language": "typescript",
            }
        )
        db = self.create_component(
            {
                "name": "DatabaseLayer",
                "type": "module",
                "file_path": "src/db/postgres.ts",
                "description": "PostgreSQL connection pool and query helpers.",
                "language": "typescript",
            }
        )
        self.link_component_depends(auth["id"], db["id"], "Auth module uses PostgreSQL for user storage")

        jwt_decision = self.create_decision(
            {
                "title": "JWT over sessions",
                "reasoning": "We chose JWT over server-side sessions because the client needs a mobile app with offline-capable auth tokens. Stateless tokens simplify horizontal scaling.",
                "status": "active",
                "source": "manual",
                "source_ref": "manual",
                "created_by": "umar",
            }
        )
        pg_decision = self.create_decision(
            {
                "title": "PostgreSQL over MongoDB",
                "reasoning": "Relational data with strict ACID requirements for billing and user accounts. PostgreSQL gives us mature tooling and JSON columns where needed.",
                "status": "active",
                "source": "manual",
                "source_ref": "manual",
                "created_by": "usman",
            }
        )
        self.link_decision_about(jwt_decision["id"], auth["id"])
        self.link_decision_about(pg_decision["id"], db["id"])

        ticket = self.create_ticket(
            {
                "id": "42",
                "title": "Add refresh token rotation",
                "body": "Implement refresh token rotation in AuthModule for improved security.",
                "type": "issue",
                "status": "open",
                "created_by": "shahmeer",
            }
        )
        self.link_decision_ticket(jwt_decision["id"], ticket["id"])
        self.link_ticket_relates(ticket["id"], auth["id"])

    # ==================================================================
    # Maintenance domain — Asset and ServiceRecord operations
    # ==================================================================

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

    def list_asset_history_recent(self, asset_id: str, limit: int = 30) -> list[dict]:
        """Newest-first ServiceRecords linked to asset_id."""
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
