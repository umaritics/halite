import json
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        try:
            return iso()
        except Exception:
            pass
    text = str(value)
    if text.startswith("{") or "_DateTime__" in text:
        return None
    return text or None


class GraphRepository:
    """Unified graph access layer — works with MemoryGraphStore or Neo4jClient."""

    def __init__(self, store):
        self.store = store
        self.is_memory = hasattr(store, "nodes")

    def init_schema(self):
        self.store.init_schema()

    def find_similar_decision(self, title: str, reasoning: str = "") -> dict | None:
        """Return an existing Decision if one is similar enough to avoid duplication."""
        if self.is_memory:
            title_lower = title.lower().strip()
            for node in self.store._find_nodes("Decision"):
                existing_title = node.get("title", "").lower().strip()
                # Exact title match
                if existing_title == title_lower:
                    return node
                # High word overlap (Jaccard >= 0.6)
                t1 = set(w for w in title_lower.split() if len(w) > 3)
                t2 = set(w for w in existing_title.split() if len(w) > 3)
                if t1 and t2:
                    overlap = len(t1 & t2) / len(t1 | t2)
                    if overlap >= 0.6:
                        return node
            return None
        # Neo4j path
        rows = self.store.run_query(
            """
            MATCH (d:Decision)
            WHERE toLower(d.title) = toLower($title)
            RETURN d LIMIT 1
            """,
            {"title": title},
        )
        if rows:
            return dict(rows[0]["d"])
        # Word overlap check via Neo4j
        title_words = [w for w in title.lower().split() if len(w) > 3]
        if not title_words:
            return None
        for word in title_words[:3]:
            rows = self.store.run_query(
                """
                MATCH (d:Decision)
                WHERE toLower(d.title) CONTAINS $word
                RETURN d LIMIT 5
                """,
                {"word": word},
            )
            for r in rows:
                existing = dict(r["d"])
                e_words = set(w for w in existing.get("title", "").lower().split() if len(w) > 3)
                q_words = set(title_words)
                if e_words and q_words:
                    overlap = len(e_words & q_words) / len(e_words | q_words)
                    if overlap >= 0.6:
                        return existing
        return None

    def create_decision(self, data: dict) -> dict:
        if self.is_memory:
            return self.store.create_decision(data)
        # Deduplication: return existing decision if similar enough
        existing = self.find_similar_decision(data.get("title", ""), data.get("reasoning", ""))
        if existing:
            logger.info("Dedup: skipping duplicate decision '%s'", data.get("title"))
            return existing
        data = {**data, "id": data.get("id") or str(uuid.uuid4()), "created_at": _now(), "updated_at": _now()}
        self.store.run_query(
            """
            CREATE (d:Decision)
            SET d = $props
            RETURN d
            """,
            {"props": data},
        )
        return data

    def list_decisions(self, status: str | None = None) -> list[dict]:
        if self.is_memory:
            return self.store.list_decisions(status)
        where = "WHERE d.status = $status" if status else ""
        rows = self.store.run_query(
            f"""
            MATCH (d:Decision) {where}
            OPTIONAL MATCH (d)-[:ABOUT]->(c:Component)
            RETURN d, collect(DISTINCT c.name) as component_names
            ORDER BY d.created_at DESC
            """,
            {"status": status} if status else {},
        )
        return [
            {**dict(r["d"]), "component_names": r.get("component_names", [])}
            for r in rows
        ]

    def get_decision(self, decision_id: str) -> dict | None:
        if self.is_memory:
            return self.store.get_decision(decision_id)
        rows = self.store.run_query(
            """
            MATCH (d:Decision {id: $id})
            OPTIONAL MATCH (d)-[:ABOUT]->(c:Component)
            OPTIONAL MATCH (d)-[:REFERENCED_IN]->(t:Ticket)
            RETURN d, collect(DISTINCT c) as components, collect(DISTINCT t) as tickets
            """,
            {"id": decision_id},
        )
        if not rows:
            return None
        row = rows[0]
        d = dict(row["d"])
        d["components"] = [dict(c) for c in row["components"] if c]
        d["tickets"] = [dict(t) for t in row["tickets"] if t]
        return d

    def update_decision(self, decision_id: str, updates: dict) -> dict | None:
        updates = {**updates, "updated_at": _now()}
        if self.is_memory:
            return self.store.update_decision(decision_id, updates)
        rows = self.store.run_query(
            """
            MATCH (d:Decision {id: $id})
            SET d += $updates
            RETURN d
            """,
            {"id": decision_id, "updates": updates},
        )
        return dict(rows[0]["d"]) if rows else None

    def delete_decision(self, decision_id: str) -> bool:
        if self.is_memory:
            return self.store.delete_decision(decision_id)
        self.store.run_query("MATCH (d:Decision {id: $id}) DETACH DELETE d", {"id": decision_id})
        return True

    def link_decision_about(self, decision_id: str, component_id: str, confidence: float = 1.0):
        if self.is_memory:
            self.store.link_decision_about(decision_id, component_id, confidence)
            return
        self.store.run_query(
            """
            MATCH (d:Decision {id: $did}), (c:Component {id: $cid})
            MERGE (d)-[r:ABOUT]->(c)
            SET r.confidence = $confidence
            """,
            {"did": decision_id, "cid": component_id, "confidence": confidence},
        )

    def link_decision_ticket(self, decision_id: str, ticket_id: str):
        if self.is_memory:
            self.store.link_decision_ticket(decision_id, ticket_id)
            return
        self.store.run_query(
            """
            MATCH (d:Decision {id: $did}), (t:Ticket {id: $tid})
            MERGE (d)-[:REFERENCED_IN]->(t)
            """,
            {"did": decision_id, "tid": ticket_id},
        )

    def link_decision_document(self, decision_id: str, document_id: str):
        if self.is_memory:
            self.store.link_decision_document(decision_id, document_id)
            return
        self.store.run_query(
            """
            MATCH (d:Decision {id: $did}), (doc:Document {id: $docid})
            MERGE (d)-[:EXTRACTED_FROM]->(doc)
            """,
            {"did": decision_id, "docid": document_id},
        )

    def find_or_create_component_by_name(self, name: str) -> dict:
        if self.is_memory:
            found = self.store.find_component_by_name(name)
            if found:
                return found
            return self.store.create_component(
                {"name": name, "type": "module", "file_path": "", "description": "", "language": "unknown"}
            )
        # On Neo4j: first try to find an existing component with this name (case-insensitive)
        rows = self.store.run_query(
            """
            MATCH (c:Component)
            WHERE toLower(c.name) = toLower($name)
            RETURN c
            ORDER BY c.file_path DESC
            LIMIT 1
            """,
            {"name": name},
        )
        if rows:
            return dict(rows[0]["c"])
        # Only create if truly not found
        rows = self.store.run_query(
            """
            MERGE (c:Component {name: $name})
            ON CREATE SET c.id = randomUUID(), c.type = 'module', c.file_path = '',
                          c.description = '', c.language = 'unknown',
                          c.created_at = datetime(), c.updated_at = datetime()
            RETURN c
            """,
            {"name": name},
        )
        return dict(rows[0]["c"])

    def find_component_by_path(self, file_path: str) -> dict | None:
        if self.is_memory:
            return self.store.find_component_by_path(file_path)
        rows = self.store.run_query(
            "MATCH (c:Component {file_path: $path}) RETURN c LIMIT 1",
            {"path": file_path},
        )
        return dict(rows[0]["c"]) if rows else None

    def create_component(self, data: dict) -> dict:
        if self.is_memory:
            return self.store.create_component(data)
        data = {**data, "id": data.get("id") or str(uuid.uuid4()), "created_at": _now(), "updated_at": _now()}
        if data.get("file_path"):
            self.store.run_query(
                """
                MERGE (c:Component {file_path: $file_path})
                ON CREATE SET c = $props
                ON MATCH SET c += $props, c.updated_at = $updated_at
                RETURN c
                """,
                {"file_path": data["file_path"], "props": data, "updated_at": _now()},
            )
        else:
            self.store.run_query("CREATE (c:Component) SET c = $props RETURN c", {"props": data})
        return data

    def create_commit(self, data: dict) -> dict:
        if self.is_memory:
            return self.store.create_commit(data)
        self.store.run_query(
            """
            MERGE (c:Commit {id: $id})
            ON CREATE SET c = $props
            RETURN c
            """,
            {"id": data["id"], "props": {**data, "created_at": _now()}},
        )
        return data

    def create_ticket(self, data: dict) -> dict:
        if self.is_memory:
            return self.store.create_ticket(data)
        self.store.run_query(
            """
            MERGE (t:Ticket {id: $id})
            ON CREATE SET t = $props
            RETURN t
            """,
            {"id": data["id"], "props": {**data, "created_at": data.get("created_at", _now())}},
        )
        return data

    def create_document(self, data: dict) -> dict:
        if self.is_memory:
            return self.store.create_document(data)
        data = {**data, "id": data.get("id") or str(uuid.uuid4()), "upload_date": _now()}
        self.store.run_query("CREATE (d:Document) SET d = $props RETURN d", {"props": data})
        return data

    def list_components(self) -> list[dict]:
        if self.is_memory:
            return self.store.list_components()
        rows = self.store.run_query("MATCH (c:Component) RETURN c ORDER BY c.name")
        return [dict(r["c"]) for r in rows]

    def list_tickets(self) -> list[dict]:
        if self.is_memory:
            return self.store.list_tickets()
        rows = self.store.run_query("MATCH (t:Ticket) RETURN t ORDER BY t.created_at DESC")
        return [dict(r["t"]) for r in rows]

    def search_entities(self, entities: list[str]) -> tuple[list[dict], list[dict]]:
        if self.is_memory:
            return self.store.search_entities(entities)
        components, decisions = [], []
        seen_c, seen_d = set(), set()
        for entity in entities[:15]:
            if not entity or len(entity.strip()) < 2:
                continue
            crows = self.store.run_query(
                """
                MATCH (c:Component)
                WHERE toLower(c.name) CONTAINS toLower($name)
                   OR toLower(c.file_path) CONTAINS toLower($name)
                RETURN c LIMIT 8
                """,
                {"name": entity},
            )
            for r in crows:
                node = dict(r["c"])
                if node.get("id") not in seen_c:
                    seen_c.add(node["id"])
                    components.append(node)
            drows = self.store.run_query(
                """
                MATCH (d:Decision)
                WHERE toLower(d.title) CONTAINS toLower($name)
                   OR toLower(coalesce(d.reasoning, '')) CONTAINS toLower($name)
                OPTIONAL MATCH (d)-[:ABOUT]->(c:Component)
                RETURN d, collect(DISTINCT c.name) as component_names
                LIMIT 8
                """,
                {"name": entity},
            )
            for r in drows:
                node = {**dict(r["d"]), "component_names": r.get("component_names") or []}
                if node.get("id") not in seen_d:
                    seen_d.add(node["id"])
                    decisions.append(node)
        return components[:20], decisions[:20]

    def graph_overview(self, limit: int = 200) -> dict:
        if self.is_memory:
            return self.store.graph_overview(limit)
        nodes_rows = self.store.run_query(
            """
            MATCH (n)
            WHERE n:Component OR n:Decision OR n:Commit OR n:Ticket OR n:Document
            RETURN n, labels(n)[0] as label
            LIMIT $limit
            """,
            {"limit": limit},
        )
        nodes = []
        for r in nodes_rows:
            node = dict(r["n"])
            node["label"] = r["label"]
            nodes.append(node)
        node_ids = [n["id"] for n in nodes]
        edges_rows = self.store.run_query(
            """
            MATCH (a)-[r]->(b)
            WHERE a.id IN $ids AND b.id IN $ids
            RETURN a.id as source, b.id as target, type(r) as type, properties(r) as properties
            """,
            {"ids": node_ids},
        )
        return {"nodes": nodes, "edges": [dict(e) for e in edges_rows]}

    def get_neighborhood(self, node_id: str) -> dict:
        if self.is_memory:
            return self.store.get_neighborhood(node_id)
        rows = self.store.run_query(
            """
            MATCH (n {id: $id})
            OPTIONAL MATCH (n)-[r]-(m)
            RETURN n, labels(n)[0] as nlabel,
                   collect({node: m, type: type(r), label: labels(m)[0]}) as neighbors
            """,
            {"id": node_id},
        )
        if not rows:
            return {}
        row = rows[0]
        node = dict(row["n"])
        node["label"] = row.get("nlabel")
        neighbors = []
        for n in row["neighbors"]:
            if not n.get("node"):
                continue
            neighbor = dict(n["node"])
            neighbor["label"] = n.get("label")
            neighbors.append({"node": neighbor, "relationship": n["type"]})
        return {"node": node, "neighbors": neighbors}

    def get_alerts(self) -> list[dict]:
        if self.is_memory:
            return self.store.get_alerts()
        rows = self.store.run_query(
            """
            MATCH (d:Decision {status: 'needs_review'})
            OPTIONAL MATCH (commit:Commit)-[mi:MAY_INVALIDATE]->(d)
            OPTIONAL MATCH (d)-[:ABOUT]->(c:Component)
            RETURN d, commit, c, mi.reason as reason
            ORDER BY d.updated_at DESC
            """
        )
        alerts = []
        for r in rows:
            decision = dict(r["d"])
            commit = dict(r["commit"]) if r["commit"] else None
            if commit:
                commit["timestamp"] = _iso(commit.get("timestamp")) or _iso(commit.get("created_at"))
            flagged = (
                _iso(decision.get("updated_at"))
                or (commit.get("timestamp") if commit else None)
                or _iso(decision.get("created_at"))
            )
            decision["updated_at"] = _iso(decision.get("updated_at"))
            decision["created_at"] = _iso(decision.get("created_at"))
            alerts.append(
                {
                    "decision": decision,
                    "commit": commit,
                    "component": dict(r["c"]) if r["c"] else None,
                    "reason": r.get("reason"),
                    "flagged_at": flagged,
                }
            )
        return alerts

    def export_agent_context(self) -> str:
        """Return a compact markdown context pack for IDE agents."""
        components = sorted(self.list_components(), key=lambda c: (c.get("name") or "").lower())
        tickets = {str(t.get("id")): t for t in self.list_tickets()}
        alerts = {
            a["decision"]["id"]: a
            for a in self.get_alerts()
            if a.get("decision", {}).get("id")
        }

        lines = [
            "# Halite Agent Context",
            "",
            "This file is an exported project-memory snapshot for IDE agents.",
            "Use it to narrow code exploration, then verify the minimum necessary files.",
            "",
            "## Working rules",
            "- Prefer cited file paths over broad repository scans.",
            "- Treat decisions with status `needs_review` or `invalidated` as risky.",
            "- Verify the referenced files before making code changes.",
            "",
            "## Components",
        ]

        for component in components:
            neighborhood = self.get_neighborhood(component["id"]) or {}
            decisions = []
            dependencies = []
            related_tickets = []

            for item in neighborhood.get("neighbors", []):
                node = item.get("node") or {}
                rel = item.get("relationship")
                label = node.get("label")
                if label == "Decision" and node.get("title"):
                    decisions.append(node)
                elif label == "Component" and rel == "DEPENDS_ON":
                    dependencies.append(node)
                elif label == "Ticket" and node.get("title"):
                    related_tickets.append(node)

            lines.extend(
                [
                    "",
                    f"### {component.get('name') or 'UnnamedComponent'}",
                    f"- Type: {component.get('type', 'module')}",
                    f"- File: {component.get('file_path') or 'N/A'}",
                    f"- Description: {component.get('description') or 'No description recorded.'}",
                ]
            )

            if dependencies:
                dep_names = ", ".join(
                    f"{d.get('name')} ({d.get('file_path') or 'no path'})" for d in dependencies
                )
                lines.append(f"- Depends on: {dep_names}")

            if not decisions:
                lines.append("- Decisions: none linked")
                continue

            lines.append("- Decisions:")
            for decision in decisions:
                status = decision.get("status", "active")
                lines.append(f"  - {decision.get('title')} [{status}]")
                reasoning = (decision.get("reasoning") or "").strip()
                if reasoning:
                    lines.append(f"    - Why it exists: {reasoning}")
                lines.append(
                    f"    - Source: {decision.get('source', 'unknown')} ({decision.get('source_ref', '')})"
                )

                linked = self.get_decision(decision["id"]) if decision.get("id") else None
                if linked:
                    dtickets = linked.get("tickets") or []
                    for ticket in dtickets:
                        t = tickets.get(str(ticket.get("id")), ticket)
                        related_tickets.append(t)

                if decision.get("id") in alerts:
                    alert = alerts[decision["id"]]
                    commit = alert.get("commit")
                    trigger = "unknown change"
                    if commit:
                        changed = ", ".join(commit.get("files_changed") or [])
                        trigger = f"commit {str(commit.get('id', ''))[:8]} touching {changed or 'tracked files'}"
                    lines.append(f"    - Alert: needs review due to {trigger}")

            if related_tickets:
                seen = set()
                lines.append("- Related tickets:")
                for ticket in related_tickets:
                    tid = str(ticket.get("id", ""))
                    if tid in seen:
                        continue
                    seen.add(tid)
                    lines.append(
                        f"  - #{tid} {ticket.get('title', '')} [{ticket.get('status', 'open')}]"
                    )

        return "\n".join(lines).strip() + "\n"

    def link_commit_modified(self, commit_id: str, component_id: str):
        if self.is_memory:
            self.store.link_commit_modified(commit_id, component_id)
            return
        self.store.run_query(
            """
            MATCH (commit:Commit {id: $cid}), (comp:Component {id: $compid})
            MERGE (commit)-[:MODIFIED]->(comp)
            """,
            {"cid": commit_id, "compid": component_id},
        )

    def invalidate_decisions_for_files(self, commit_sha: str, changed_files: list[str]) -> list[dict]:
        flagged = []
        for file_path in changed_files:
            component = self.find_component_by_path(file_path)
            if not component:
                continue
            if self.is_memory:
                for n in self.store._neighbors(component["id"]):
                    if n["node"]["label"] == "Decision" and n["relationship"] == "ABOUT":
                        decision = n["node"]
                        if decision.get("status") == "active":
                            self.store.update_decision(decision["id"], {"status": "needs_review"})
                            self.store.link_commit_may_invalidate(
                                commit_sha, decision["id"], f"file modified: {file_path}"
                            )
                            flagged.append({"decision_id": decision["id"], "title": decision["title"]})
            else:
                rows = self.store.run_query(
                    """
                    MATCH (c:Component {file_path: $file_path})
                    MATCH (d:Decision)-[:ABOUT]->(c)
                    WHERE d.status = 'active'
                    SET d.status = 'needs_review', d.updated_at = datetime()
                    WITH d
                    MATCH (commit:Commit {id: $commit_sha})
                    MERGE (commit)-[r:MAY_INVALIDATE]->(d)
                    SET r.reason = $reason
                    RETURN d.id as decision_id, d.title as title
                    """,
                    {
                        "file_path": file_path,
                        "commit_sha": commit_sha,
                        "reason": f"file modified: {file_path}",
                    },
                )
                flagged.extend(rows)
        return flagged

    def seed_demo_data(self):
        if self.is_memory:
            self.store.seed_demo_data()
            return

        # Skip if Neo4j already has decisions
        existing = self.store.run_query("MATCH (d:Decision) RETURN count(d) as c")
        if existing and existing[0].get("c", 0) > 0:
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
        self.store.run_query(
            """
            MATCH (a:Component {id: $a}), (b:Component {id: $b})
            MERGE (a)-[:DEPENDS_ON {description: $desc}]->(b)
            """,
            {
                "a": auth["id"],
                "b": db["id"],
                "desc": "Auth module uses PostgreSQL for user storage",
            },
        )

        jwt = self.create_decision(
            {
                "title": "JWT over sessions",
                "reasoning": "We chose JWT over server-side sessions because the client needs a mobile app with offline-capable auth tokens. Stateless tokens simplify horizontal scaling.",
                "status": "active",
                "source": "manual",
                "source_ref": "manual",
                "created_by": "umar",
            }
        )
        pg = self.create_decision(
            {
                "title": "PostgreSQL over MongoDB",
                "reasoning": "Relational data with strict ACID requirements for billing and user accounts. PostgreSQL gives us mature tooling and JSON columns where needed.",
                "status": "active",
                "source": "manual",
                "source_ref": "manual",
                "created_by": "usman",
            }
        )
        self.link_decision_about(jwt["id"], auth["id"])
        self.link_decision_about(pg["id"], db["id"])

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
        self.link_decision_ticket(jwt["id"], ticket["id"])
        self.store.run_query(
            """
            MATCH (t:Ticket {id: $tid}), (c:Component {id: $cid})
            MERGE (t)-[:RELATES_TO]->(c)
            """,
            {"tid": ticket["id"], "cid": auth["id"]},
        )

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

    # ==================================================================
    # Maintenance domain — Asset and ServiceRecord operations
    # ==================================================================

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
            "jasc_code": data.get("jasc_code", ""),
            "text": data.get("text", ""),
            "status": data.get("status", "auto_accepted"),
            "confidence": data.get("confidence", 1.0),
            "source": data.get("source", "faa_sdr"),
            "id": data.get("id") or str(uuid.uuid4()),
            "created_at": data.get("created_at") or _now(),
            "updated_at": _now(),
        }
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

    def list_asset_history(self, asset_id: str, limit: int = 50) -> list[dict]:
        """Return ServiceRecords for an asset ordered ascending by occurred_at."""
        if self.is_memory:
            return self.store.list_asset_history(asset_id, limit)
        rows = self.store.run_query(
            """
            MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset {id: $aid})
            RETURN sr
            ORDER BY sr.occurred_at ASC
            LIMIT $limit
            """,
            {"aid": asset_id, "limit": limit},
        )
        return [dict(r["sr"]) for r in rows]

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

    def list_service_records(
        self, status: str | None = None, asset_id: str | None = None
    ) -> list[dict]:
        """List ServiceRecords, optionally filtered by status and/or asset_id."""
        if self.is_memory:
            return self.store.list_service_records(status, asset_id)
        where_clauses = []
        params: dict = {}
        if status:
            where_clauses.append("sr.status = $status")
            params["status"] = status
        if asset_id:
            where_clauses.append("a.id = $asset_id")
            params["asset_id"] = asset_id
        where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        match = (
            "MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset)"
            if asset_id
            else "MATCH (sr:ServiceRecord) OPTIONAL MATCH (sr)-[:ABOUT]->(a:Asset)"
        )
        rows = self.store.run_query(
            f"""
            {match}
            {where}
            RETURN sr
            ORDER BY sr.occurred_at DESC
            """,
            params,
        )
        return [dict(r["sr"]) for r in rows]

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
