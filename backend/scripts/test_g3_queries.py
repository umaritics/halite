import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json

try:
    assets_res = requests.get('http://localhost:8000/api/maintenance/assets')
    assets = assets_res.json()
    targets = {a['tail_number']: a['id'] for a in assets if a['tail_number'] in ['813SK', '508AE', '860NW']}
    print('Targets found:', list(targets.keys()))
    
    queries = {
        '813SK': 'slide light will not extinguish at door 1R',
        '508AE': 'RH IDG failing',
        '860NW': 'A/C PACK INOP'
    }
    
    for tail, symptom in queries.items():
        if tail not in targets:
            print(f'Skipping {tail} — not in DB')
            continue
            
        print(f'\n--- Diagnosing {tail}: {symptom} ---')
        res = requests.post('http://localhost:8000/api/maintenance/diagnose', json={'asset_id': targets[tail], 'symptom_text': symptom})
        if res.status_code == 200:
            data = res.json()
            print('Top 3 ranked checks:')
            for check in data['ranked_checks'][:3]:
                print(f"  {check['rank']}. {check['part_name']} (score: {check['score']}, count: {check['evidence_count']})")
            print('\nExplanation:')
            print(data['explanation'])
            print(f"\nContext: {data['context_size']['asset_records']} asset records, {data['context_size']['fleet_records']} fleet records")
            print(f"Validation: {data['citation_validation']}")
        else:
            print(f'Error: {res.status_code}', res.text)
            
except Exception as e:
    print('Error:', e)
