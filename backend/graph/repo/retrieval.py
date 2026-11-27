import logging

logger = logging.getLogger(__name__)


class RetrievalMixin:
    """Retrieval graph operations; preserved from the pre-split implementation."""

    def graph_overview(self, limit: int = 200) -> dict:
        if self.is_memory:
            return self.store.graph_overview(limit)
        nodes_rows = self.store.run_query(
            """
            MATCH (n)
            WHERE n:Component OR n:Decision OR n:Commit OR n:Ticket OR n:Document OR n:Asset OR n:ServiceRecord
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

    def list_asset_history_recent(self, asset_id: str, limit: int = 30) -> list[dict]:
        """Newest-first ServiceRecords for an asset (diagnostic context)."""
        if self.is_memory:
            return self.store.list_asset_history_recent(asset_id, limit)
        rows = self.store.run_query(
            """
            MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset {id: $aid})
            OPTIONAL MATCH (corrector:ServiceRecord)-[:SUPERSEDES]->(sr)
            RETURN sr,
                   head(collect(CASE WHEN corrector IS NULL THEN null
                            ELSE {record_id: corrector.record_id, part_name: corrector.part_name}
                       END)) AS corrected_by
            ORDER BY sr.occurred_at DESC
            LIMIT $limit
            """,
            {"aid": asset_id, "limit": limit},
        )
        out = []
        for row in rows:
            rec = dict(row["sr"])
            if row.get("corrected_by"):
                rec["corrected_by"] = dict(row["corrected_by"])
            out.append(rec)
        return out

    def get_service_records_by_ids(self, record_ids: list[str]) -> list[dict]:
        """Batch fetch ServiceRecords by record_id (order not guaranteed)."""
        if not record_ids:
            return []
        if self.is_memory:
            return self.store.get_service_records_by_ids(record_ids)
        rows = self.store.run_query(
            """
            MATCH (sr:ServiceRecord)
            WHERE sr.record_id IN $ids
            RETURN sr
            """,
            {"ids": list(record_ids)},
        )
        return [dict(r["sr"]) for r in rows]

    def list_service_records(
        self,
        status: str | None = None,
        asset_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """List ServiceRecords, optionally filtered by status and/or asset_id.

        When ``limit`` is set, Cypher applies LIMIT (newest-first by occurred_at).
        """
        if self.is_memory:
            return self.store.list_service_records(status, asset_id, limit=limit)
        where_clauses = []
        params: dict = {}
        if status:
            where_clauses.append("sr.status = $status")
            params["status"] = status
        if asset_id:
            where_clauses.append("a.id = $asset_id")
            params["asset_id"] = asset_id
        where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        # A WHERE directly after OPTIONAL MATCH is scoped to that optional
        # pattern and does not remove the ServiceRecord row.  Project first so
        # status/asset filters constrain the complete row set.
        match = "MATCH (sr:ServiceRecord) OPTIONAL MATCH (sr)-[:ABOUT]->(a:Asset) WITH sr, a"
        limit_clause = ""
        if limit is not None:
            params["limit"] = int(limit)
            limit_clause = "LIMIT $limit"
        rows = self.store.run_query(
            f"""
            {match}
            {where}
            OPTIONAL MATCH (corrector:ServiceRecord)-[:SUPERSEDES]->(sr)
            WITH sr, a, head(collect(CASE WHEN corrector IS NULL THEN null ELSE {{record_id: corrector.record_id, part_name: corrector.part_name}} END)) AS corrected_by
            RETURN sr, a.id AS asset_id, a.tail_number AS tail_number, corrected_by
            ORDER BY sr.occurred_at DESC
            {limit_clause}
            """,
            params,
        )
        result = []
        for row in rows:
            record = {
                **dict(row["sr"]),
                "asset_id": row["asset_id"],
                "tail_number": row["tail_number"],
                "classification": dict(row["sr"]).get("classification_label"),
            }
            if row.get("corrected_by"):
                record["corrected_by"] = dict(row["corrected_by"])
            result.append(record)
        return result


