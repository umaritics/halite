"""
Run find_candidate_pairs on a specific record from 813SK to get the log line
history=N candidates=M that is the key demo artefact.
"""
import logging, os, sys
logging.basicConfig(level=logging.INFO)
sys.path.insert(0, '.')
os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
os.environ['NEO4J_USERNAME'] = 'neo4j'
os.environ['NEO4J_PASSWORD'] = 'localdevpassword'

from graph.neo4j_client import Neo4jClient
from graph.queries import GraphRepository
from services.conflict_engine import find_candidate_pairs

c = Neo4jClient(os.environ['NEO4J_URI'], os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD'])
r = GraphRepository(c)

# Get a non-first record from 813SK to show real history
q = """
MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset {tail_number: '813SK'})
RETURN sr.record_id AS rid, sr.occurred_at AS date
ORDER BY sr.occurred_at DESC
LIMIT 1
"""
rows = c.run_query(q)
if not rows:
    print('No records for 813SK')
    sys.exit(1)

demo_record_id = rows[0]['rid']
print(f'Demo record: {demo_record_id}  date={rows[0]["date"]}')

# Run find_candidate_pairs — this emits the key log line
candidates = find_candidate_pairs(r, demo_record_id, max_candidates=25)
print(f'candidates returned: {len(candidates)}')
if candidates:
    print('Top candidate:', candidates[0]['record']['record_id'], 'score:', candidates[0]['score'])
