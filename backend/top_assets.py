import os, sys
sys.path.insert(0, '.')
os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
os.environ['NEO4J_USERNAME'] = 'neo4j'
os.environ['NEO4J_PASSWORD'] = 'localdevpassword'
from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository
c = Neo4jClient(os.environ['NEO4J_URI'], os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD'])
r = GraphRepository(c)

rows = c.run_query('''
MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset)
RETURN a.tail_number AS tail, a.id AS asset_id, count(sr) AS n
ORDER BY n DESC
LIMIT 10
''')
print('TOP 10 ASSETS BY RECORD COUNT:')
for row in rows:
    print(f"  tail={row['tail']}  asset_id={row['asset_id']}  n={row['n']}")
