import json
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GraphRepository:
    """Unified graph access layer — works with MemoryGraphStore or Neo4jClient."""

    def __init__(self, store):
        self.store = store
        self.is_memory = hasattr(store, "nodes")

    def init_schema(self):
        self.store.init_schema()

    def create_decision(self, data: dict) -> dict:
        if self.is_memory:
            return self.store.create_decision(data)
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
        for entity in entities[:5]:
            crows = self.store.run_query(
                """
                MATCH (c:Component)
                WHERE toLower(c.name) CONTAINS toLower($name)
                   OR toLower(c.file_path) CONTAINS toLower($name)
                RETURN c LIMIT 5
                """,
                {"name": entity},
            )
            components.extend([dict(r["c"]) for r in crows])
            drows = self.store.run_query(
                """
                MATCH (d:Decision)
                WHERE toLower(d.title) CONTAINS toLower($name)
                   OR toLower(d.reasoning) CONTAINS toLower($name)
                RETURN d LIMIT 5
                """,
                {"name": entity},
            )
            decisions.extend([dict(r["d"]) for r in drows])
        return components[:10], decisions[:10]

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
            RETURN n, collect({node: m, type: type(r)}) as neighbors
            """,
            {"id": node_id},
        )
        if not rows:
            return {}
        row = rows[0]
        return {
            "node": dict(row["n"]),
            "neighbors": [
                {"node": dict(n["node"]), "relationship": n["type"]}
                for n in row["neighbors"]
                if n.get("node")
            ],
        }

    def get_alerts(self) -> list[dict]:
        if self.is_memory:
            return self.store.get_alerts()
        rows = self.store.run_query(
            """
            MATCH (d:Decision {status: 'needs_review'})
            OPTIONAL MATCH (commit:Commit)-[mi:MAY_INVALIDATE]->(d)
            OPTIONAL MATCH (d)-[:ABOUT]->(c:Component)
            RETURN d, commit, c, mi.reason as reason
            """
        )
        return [
            {
                "decision": dict(r["d"]),
                "commit": dict(r["commit"]) if r["commit"] else None,
                "component": dict(r["c"]) if r["c"] else None,
                "reason": r.get("reason"),
            }
            for r in rows
        ]

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
