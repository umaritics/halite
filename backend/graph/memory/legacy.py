

class LegacyMixin:
    """Legacy graph operations; preserved from the pre-split implementation."""

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


