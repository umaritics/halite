"""Create a reproducible standard-library-only runner bundle for the M4."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from investigation.experiments.model_compare import load_packet

WRAPPER='''"""Run the frozen Halite model comparison after extracting this folder."""
from pathlib import Path
import hashlib
import json
import runpy
import sys
root=Path(__file__).resolve().parent
manifest=json.loads((root/'BUNDLE_MANIFEST.json').read_text())
for name,expected in manifest['files_sha256'].items():
    target=(root/name).resolve()
    if not target.is_relative_to(root) or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
        raise SystemExit('Bundle file differs from its manifest: '+name)
sys.path.insert(0,str(root))
if any(a=='--packet' or a.startswith('--packet=') for a in sys.argv[1:]):
    raise SystemExit('The portable runner uses its bundled frozen packet; do not replace it.')
sys.argv[1:1]=['--packet',str(Path(__file__).with_name('model_prompts_2024_v1.json'))]
runpy.run_module('investigation.experiments.model_compare',run_name='__main__')
'''


def build(packet,output,readme):
    data=load_packet(packet)
    output=Path(output)
    if output.exists():raise FileExistsError('Preserve published bundles; choose a fresh output path.')
    root=Path(__file__).parents[2]
    names=['investigation/__init__.py','investigation/grounding.py','investigation/embed_port.py',
           'investigation/data/grounding_parts_v1.json','investigation/experiments/model_compare.py',
           'investigation/experiments/model_prompts.py']
    files={name:(root/name).read_bytes() for name in names}
    files.update({'investigation/experiments/__init__.py':b'', 'run_compare.py':WRAPPER.encode(),
                  'README.md':Path(readme).read_bytes(),'model_prompts_2024_v1.json':Path(packet).read_bytes()})
    manifest={'version':'portable-model-runner-v1','packet_sha256':data['packet_sha256'],
              'files_sha256':{name:hashlib.sha256(raw).hexdigest() for name,raw in sorted(files.items())},
              'dependencies':'Python 3.10+ standard library only; models/Ollama must already be installed; no automatic installation.'}
    files['BUNDLE_MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,raw)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n')
    return manifest,digest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('packet','output','readme'):parser.add_argument('--'+key,required=True)
    args=parser.parse_args();manifest,digest=build(**vars(args));print(json.dumps({'files':len(manifest['files_sha256']),'zip_sha256':digest}))
