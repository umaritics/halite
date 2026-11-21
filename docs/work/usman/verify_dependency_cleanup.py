"""Audit actual imports and hosted pip evidence; standard library only."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
REMOVED_DIRECT = {'langchain', 'langchain-community', 'langchain-text-splitters', 'python-docx', 'python-dotenv', 'pypdf', 'docx2txt'}
REMOVED_ROOTS = {'langchain', 'langchain_community', 'langchain_text_splitters', 'docx', 'dotenv', 'pypdf', 'docx2txt'}


def canonical(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def direct_names(text):
    return {canonical(re.match(r'[A-Za-z0-9_.-]+', line).group()) for line in text.splitlines()
            if line.strip() and not line.startswith(('#', '-'))}


def audit(install_report=None, installed=None):
    before = json.loads((ROOT / 'docs/work/usman/evidence/phase12-dependencies/baseline.json').read_text())
    assert hashlib.sha256(before['requirements'].encode()).hexdigest() == before['requirements_sha256']
    current = (ROOT / 'backend/requirements.txt').read_text()
    direct = direct_names(current)
    assert not REMOVED_DIRECT & direct, 'An unused direct requirement returned.'
    assert 'pandas' in direct and 'numpy==1.26.4' in current, 'Preserve the verified CSV dependency/NumPy baseline.'
    imports = {}
    files = 0
    for path in sorted((ROOT / 'backend').rglob('*.py')):
        if any(part in {'.venv', 'venv', 'node_modules'} for part in path.parts):
            continue
        files += 1
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                function = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
                if function in {'__import__', 'import_module'}:
                    names = [node.args[0].value]
            for name in names:
                imports.setdefault(name.split('.')[0], []).append(f'{path.relative_to(ROOT)}:{node.lineno}')
    assert not REMOVED_ROOTS & imports.keys(), 'A removed dependency is actually imported.'
    summary = {'baseline': {key: before[key] for key in ('source_commit', 'workflow_url', 'requirements_sha256')},
               'backend_python_files_audited': files,
               'removed_direct_requirements': sorted(direct_names(before['requirements']) - direct),
               'added_direct_constraints': sorted(direct - direct_names(before['requirements'])),
               'removed_imports_found': {name: imports.get(name, []) for name in sorted(REMOVED_ROOTS)},
               'required_pandas_imports': imports.get('pandas', []),
               'required_requests_imports': imports.get('requests', []),
               'note': 'python-dotenv remains required transitively; NumPy was already installed and is pinned to the verified baseline.'}
    assert summary['required_pandas_imports'], 'Do not describe pandas as unused.'
    assert 'requests' in direct and summary['required_requests_imports'], 'Retained verification scripts require requests.'
    if install_report is not None:
        assert installed is not None, 'Installed-environment evidence is also required.'
        selected = {canonical(row['metadata']['name']): row['metadata']['version'] for row in install_report['install']}
        actual = {canonical(row['name']): row['version'] for row in installed}
        assert actual['numpy'] == before['installed_transaction']['numpy'] == '1.26.4'
        assert actual['pandas'] == before['installed_transaction']['pandas'] == '2.2.2'
        assert actual['requests'] == before['installed_transaction']['requests']
        assert 'python-dotenv' in actual and 'pydantic-settings' in actual
        assert not any(name.startswith(('langchain', 'langsmith')) or name in {'python-docx', 'pypdf', 'docx2txt'} for name in actual)
        old = before['installed_transaction']
        summary.update(hosted_installed=actual, hosted_install_transaction=selected,
                       no_longer_selected_packages=sorted(set(old) - set(selected)),
                       new_selected_packages=sorted(set(selected) - set(old)),
                       baseline_transaction_count=len(old), hosted_transaction_count=len(selected))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-report', type=Path)
    parser.add_argument('--installed', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text()) if path else None
    result = json.dumps(audit(read(args.install_report), read(args.installed)), indent=2) + '\n'
    if args.output:
        args.output.write_text(result)
    else:
        print(result, end='')
