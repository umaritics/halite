import os, sys, csv
sys.path.insert(0, '.')
os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
os.environ['NEO4J_USERNAME'] = 'neo4j'
os.environ['NEO4J_PASSWORD'] = 'localdevpassword'
from graph.neo4j_client import Neo4jClient
c = Neo4jClient(os.environ['NEO4J_URI'], os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD'])

# Check what GT pairs involve 813SK, 508AE, 860NW
gt_path = 'data/processed/ground_truth_pairs.csv'
with open(gt_path) as f:
    reader = csv.DictReader(f)
    pairs = list(reader)

print(f'Total GT pairs: {len(pairs)}')
print('Sample pair:', pairs[0] if pairs else None)

# Check if any GT pair records are in 813SK
top_tails = ['813SK', '508AE', '860NW']
for tail in top_tails:
    q = f"MATCH (sr:ServiceRecord)-[:ABOUT]->(a:Asset {{tail_number: '{tail}'}}) RETURN sr.record_id AS rid"
    rids = {row['rid'] for row in c.run_query(q)}
    in_gt = [p for p in pairs if p['superseding_record_id'] in rids]
    print(f'{tail}: {len(rids)} records, {len(in_gt)} in GT pairs')
    if in_gt:
        print('  GT pair:', in_gt[0])
