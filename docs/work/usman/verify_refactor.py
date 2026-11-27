import ast,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[3]
result={}
for old,pkg,cls in [('queries.py','repo','GraphRepository'),('memory_store.py','memory','MemoryGraphStore')]:
 original=subprocess.check_output(['git','show',f'0dd86d9:backend/graph/{old}'],cwd=root,text=True)
 original_class=next(n for n in ast.parse(original).body if isinstance(n,ast.ClassDef))
 before={n.name:ast.dump(n,include_attributes=False) for n in original_class.body if isinstance(n,ast.FunctionDef)}
 after={}
 for f in (root/'backend/graph'/pkg).glob('*.py'):
  for n in ast.walk(ast.parse(f.read_text())):
   if isinstance(n,ast.FunctionDef):after[n.name]=ast.dump(n,include_attributes=False)
 changed=[name for name,node in before.items() if after.get(name)!=node]
 assert not changed, changed
 result[cls]={'method_count':len(before),'all_method_bodies_and_signatures_identical':True}
original=subprocess.check_output(['git','show','0dd86d9:backend/db/models.py'],cwd=root,text=True)
assert original==(root/'backend/db/models/identity.py').read_text()
result['identity_models']={'byte_identical_to_baseline':True,'table_count':5}
# Compare all original test files, allowing only the owner-authored upstream fix.
paths=subprocess.check_output(['git','ls-tree','-r','--name-only','0dd86d9','backend/tests'],cwd=root,text=True).splitlines()
changed=[]
for name in paths:
    revision='797778a' if name=='backend/tests/test_api_maintenance.py' else '0dd86d9'
    expected=subprocess.check_output(['git','show',f'{revision}:{name}'],cwd=root)
    if (root/name).read_bytes()!=expected:changed.append(name)
assert not changed,changed
result['existing_tests']={'unexpected_modifications':changed, 'upstream_owner_fix':'797778a, incorporated as 4ce566c'}
print(json.dumps(result,indent=2))
