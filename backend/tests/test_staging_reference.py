"""Private-runner protocol checks; no staging connection or real model call."""
from contextlib import contextmanager
import json
import os

import pytest

from investigation.experiments import staging_reference as tool

SHA = 'a' * 40
TOKEN = 'SYNTHETIC_SECRET_DO_NOT_PERSIST'


def healthy():
    return {'git_sha': SHA, 'status': 'ok', 'demo_mode': False,
            'graph_mode': 'neo4j', 'llm_mode': 'live', 'auth_db_mode': 'postgresql',
            'llm_provider': 'openai_compatible', 'model': 'phi4-mini',
            'auth_enabled': True, 'openapi_enabled': False,
            'maintenance_corpus_loaded': True, 'maintenance_record_count': 2079}


def container():
    return {'id': 'synthetic_container', 'image': 'ollama/ollama:0.9.6',
            'running': True, 'restarts': 0, 'memory_limit': 4 * 1024**3,
            'nano_cpus': 2 * 10**9, 'ports': {'11434/tcp': None},
            'networks': {'app': {'IPAddress': '172.18.0.3'}}}


def configuration():
    return {'OPENAI_COMPAT_BASE_URL': 'http://halite-ollama:11434/v1',
            'OPENAI_COMPAT_API_KEY': TOKEN, 'GROQ_MODEL': 'phi4-mini', 'GIT_SHA': SHA,
            'LLM_PROVIDER': 'openai_compatible'}


class Remote:
    def __init__(self):
        self.commands = []
        self.active = False
        self.restarted = False

    def read_json(self, *command):
        self.commands.append(command)
        if command[:2] == ('docker', 'exec'):
            return configuration()
        result = container()
        if self.restarted and len(self.commands) > 2:
            result['restarts'] += 1
        return result

    @contextmanager
    def tunnel(self, address):
        assert address == '172.18.0.3'
        self.active = True
        try:
            yield
        finally:
            self.active = False


def mock_transport(monkeypatch):
    class Transport:
        def __init__(self, endpoint, token):
            assert endpoint == tool.ENDPOINT and token == TOKEN

        def request(self, path):
            assert path == '/api/tags'
            return {'models': [{'name': 'phi4-mini:latest'}]}
    monkeypatch.setattr(tool, 'Ollama', Transport)


def mock_compare(packet, models, output, **options):
    assert packet.name == 'model_prompts_2024_v1.json'
    assert models == ['phi4-mini:latest'] and 'client' not in options
    assert options == {'endpoint': tool.ENDPOINT, 'role': 'staging_reference', 'timeout': 600}
    assert os.environ['HALITE_MODEL_API_KEY'] == TOKEN
    output.mkdir()
    result = {'complete': True, 'n_attempts': 30, 'n_responses': 30, 'provider_errors': 0}
    (output / 'results.json').write_text(json.dumps(result))
    return result


def test_measurement_validates_boundaries_restores_token_and_never_persists_secrets(tmp_path, monkeypatch):
    mock_transport(monkeypatch)
    monkeypatch.setattr(tool, 'health', healthy)
    monkeypatch.setattr(tool, 'compare', mock_compare)
    monkeypatch.setenv('HALITE_MODEL_API_KEY', 'old_synthetic_value')
    remote = Remote()
    out = tmp_path / 'reference'
    result = tool.measure(out, SHA, remote=remote)
    assert result['n_attempts'] == 30 and not remote.active
    assert os.environ['HALITE_MODEL_API_KEY'] == 'old_synthetic_value'
    assert json.loads((out / 'status.json').read_text())['complete'] is True
    assert json.loads((out / 'status.json').read_text())['timeout_seconds'] == 600
    assert (out / 'server-after.json').exists()
    provenance = json.loads((out / 'server-provenance.json').read_text())
    assert not provenance['m4_measurement'] and not provenance['database_writes']
    assert not provenance['public_model_ports']
    assert all(TOKEN not in p.read_text() for p in out.rglob('*.json'))
    assert all(c[:2] in (('docker', 'exec'), ('docker', 'inspect')) for c in remote.commands)
    assert len(remote.commands) == 3
    with pytest.raises(FileExistsError):
        tool.measure(out, SHA, remote=remote)


@pytest.mark.parametrize('field,value', [('git_sha', 'wrong'), ('graph_mode', 'memory'),
    ('llm_mode', 'demo'), ('auth_db_mode', 'sqlite'), ('openapi_enabled', True),
    ('maintenance_record_count', 0), ('auth_enabled', False)])
def test_unhealthy_or_unversioned_runtime_fails_before_ssh_or_model(tmp_path, monkeypatch, field, value):
    data = healthy()
    data[field] = value
    monkeypatch.setattr(tool, 'health', lambda: data)
    remote = Remote()
    with pytest.raises(ValueError, match='healthy'):
        tool.measure(tmp_path / 'out', SHA, remote=remote)
    assert not remote.commands
    status = json.loads((tmp_path / 'out/status.json').read_text())
    assert not status['complete'] and status['stage'] == 'public_preflight'


def test_private_container_and_configuration_guards():
    assert tool.private_server(container()) == '172.18.0.3'
    for field, value in [('ports', {'11434/tcp': [{'HostPort': '11434'}]}),
        ('memory_limit', 0), ('nano_cpus', 0), ('running', False),
        ('image', 'unapproved'), ('networks', {'app': {'IPAddress': '8.8.8.8'}})]:
        bad = container()
        bad[field] = value
        with pytest.raises(ValueError):
            tool.private_server(bad)
    tool.server_configuration(configuration(), SHA)
    for field, value in [('GROQ_MODEL', 'different'), ('GIT_SHA', 'wrong'),
        ('OPENAI_COMPAT_API_KEY', ''), ('OPENAI_COMPAT_BASE_URL', 'http://public.example:11434/v1')]:
        bad = configuration()
        bad[field] = value
        with pytest.raises(ValueError):
            tool.server_configuration(bad, SHA)


@pytest.mark.parametrize('change', ['corpus', 'restart', 'provider'])
def test_postflight_changes_and_provider_errors_preserve_results_and_close_tunnel(tmp_path, monkeypatch, change):
    mock_transport(monkeypatch)
    before, after = healthy(), healthy()
    if change == 'corpus':
        after['maintenance_record_count'] += 1
    values = iter([before, after])
    monkeypatch.setattr(tool, 'health', lambda: next(values))
    def comparison(*args, **kwargs):
        result = mock_compare(*args, **kwargs)
        if change == 'provider':
            result['provider_errors'] = 1
        return result
    monkeypatch.setattr(tool, 'compare', comparison)
    monkeypatch.delenv('HALITE_MODEL_API_KEY', raising=False)
    remote = Remote()
    remote.restarted = change == 'restart'
    with pytest.raises(ValueError):
        tool.measure(tmp_path / 'out', SHA, remote=remote)
    assert not remote.active and 'HALITE_MODEL_API_KEY' not in os.environ
    assert (tmp_path / 'out/comparison/results.json').exists()
    status = json.loads((tmp_path / 'out/status.json').read_text())
    assert not status['complete'] and status['error_type'] == 'ValueError'
    assert (tmp_path / 'out/health-after.json').exists()
    if change == 'provider':
        assert status['stage'] == 'attempts_failed' and status['provider_errors'] == 1
        assert (tmp_path / 'out/server-after.json').exists()
        assert len(remote.commands) == 3


def test_ssh_commands_quote_metadata_code_and_require_verified_host_keys(tmp_path, monkeypatch):
    key, hosts = tmp_path / 'key', tmp_path / 'hosts'
    key.write_text('synthetic')
    hosts.write_text('synthetic')
    remote = tool.SSH('user@host.example', key, hosts)
    calls = []
    class Result:
        stdout = b'{"result":true}'
    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        return Result()
    monkeypatch.setattr(tool.subprocess, 'run', execute)
    assert remote.read_json('docker', 'exec', 'halite-api', 'python', '-c', tool.CONFIG_CODE) == {'result': True}
    assert 'StrictHostKeyChecking=yes' in calls[0][0]
    import shlex
    assert shlex.split(calls[0][0][-1])[-1] == tool.CONFIG_CODE
    assert calls[0][1]['capture_output'] is True
    with pytest.raises(ValueError):
        tool.SSH('-oProxyCommand=bad@host', key, hosts)
    with pytest.raises(ValueError):
        tool.SSH('user@host', key, tmp_path / 'missing')
    for address in ('8.8.8.8', '127.0.0.1', '::1'):
        with pytest.raises(ValueError):
            with remote.tunnel(address):
                pytest.fail('Unsafe address became reachable')


@pytest.mark.parametrize('body_fails', [False, True])
def test_tunnel_is_loopback_only_and_terminates_even_if_measurement_fails(tmp_path, monkeypatch, body_fails):
    from contextlib import nullcontext
    key, hosts = tmp_path / 'key', tmp_path / 'hosts'
    key.write_text('synthetic')
    hosts.write_text('synthetic')
    remote = tool.SSH('user@host', key, hosts)
    class Process:
        stopped = False
        def poll(self):
            return 0 if self.stopped else None
        def terminate(self):
            self.stopped = True
        def wait(self, timeout):
            assert timeout == 10
    process = Process()
    commands = []
    def start(argv, **kwargs):
        commands.append(argv)
        return process
    monkeypatch.setattr(tool.subprocess, 'Popen', start)
    monkeypatch.setattr(tool.socket, 'create_connection', lambda *a, **k: nullcontext())
    if body_fails:
        with pytest.raises(RuntimeError, match='synthetic failure'):
            with remote.tunnel('172.18.0.3'):
                raise RuntimeError('synthetic failure')
    else:
        with remote.tunnel('172.18.0.3'):
            assert not process.stopped
    assert process.stopped
    assert '127.0.0.1:11435:172.18.0.3:11434' in commands[0]
    assert 'ExitOnForwardFailure=yes' in commands[0]


def test_public_health_is_bounded_and_bad_revision_creates_no_output(tmp_path, monkeypatch):
    import io
    monkeypatch.setattr(tool, 'urlopen', lambda url, timeout: io.BytesIO(json.dumps(healthy()).encode()))
    assert tool.health() == healthy()
    monkeypatch.setattr(tool, 'urlopen', lambda url, timeout: io.BytesIO(b'x' * 65537))
    with pytest.raises(ValueError, match='size'):
        tool.health()
    with pytest.raises(ValueError, match='revision'):
        tool.measure(tmp_path / 'out', 'main', remote=Remote())
    assert not (tmp_path / 'out').exists()
