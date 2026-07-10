from neo4j import GraphDatabase

from graph.schema import SCHEMA_INDEXES


class Neo4jClient:
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.database = database
        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
            connection_timeout=30,
            max_connection_lifetime=3600,
        )
        # Fail fast with a clear error if Aura is paused / unreachable
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

    def run_query(self, query: str, parameters: dict | None = None):
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def init_schema(self):
        for index_query in SCHEMA_INDEXES:
            self.run_query(index_query)
