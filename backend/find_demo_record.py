import os, sys
sys.path.insert(0, '.')
os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
os.environ['NEO4J_USERNAME'] = 'neo4j'
os.environ['NEO4J_PASSWORD'] = 'localdevpassword'
from graph.neo4j_client import Neo4jClient
c = Neo4jClient(os.environ['NEO4J_URI'], os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD'])

q = """
MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset {tail_number: '813SK'})
WHERE sr.text CONTAINS 'SUPPLEMENTAL REPORT'
RETURN sr.record_id AS rid, sr.occurred_at AS date, left(sr.text, 100) AS text
LIMIT 5
"""
rows = c.run_query(q)
print('813SK supplemental records:')
for row in rows:
    print(row)
