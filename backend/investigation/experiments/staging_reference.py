"""Measure the existing staging model through a temporary private SSH tunnel.

This uses no application/graph/database writes, model pulls or published ports.
Runner timings include the SSH path and are never described as M4 timings.
"""
import argparse
from contextlib import contextmanager
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

from investigation.experiments.model_compare import Ollama, run as compare

HEALTH_URL = 'https://dev1.corp.curatech.pk/halite-api/api/health'
ENDPOINT = 'http://127.0.0.1:11435'
CONFIG_CODE = '''import json, os
print(json.dumps({key:os.environ.get(key, '') for key in
('OPENAI_COMPAT_BASE_URL','OPENAI_COMPAT_API_KEY','GROQ_MODEL','LLM_PROVIDER','GIT_SHA')}))'''
INSPECT = '''{"id":{{json .Id}},"image":{{json .Config.Image}},
"running":{{json .State.Running}},"restarts":{{json .RestartCount}},
"memory_limit":{{json .HostConfig.Memory}},"nano_cpus":{{json .HostConfig.NanoCpus}},
"ports":{{json .NetworkSettings.Ports}},"networks":{{json .NetworkSettings.Networks}}}'''


class SSH:
    def __init__(self, target, key, known_hosts):
        if not re.fullmatch(r'[a-z_][a-z0-9_-]*@[A-Za-z0-9][A-Za-z0-9.-]*', target):
            raise ValueError('Use an explicit SSH user and hostname without options.')
        if not Path(key).is_file() or not Path(known_hosts).is_file():
            raise ValueError('SSH key and verified known-hosts files are required.')
        self.base = ['ssh', '-i', str(key), '-o', 'BatchMode=yes', '-o',
            'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(known_hosts),
            '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15', '-o',
            'ServerAliveCountMax=2']
        self.target = target

    def read_json(self, *command):
        result = subprocess.run(self.base + [self.target, shlex.join(command)],
            capture_output=True, check=True, timeout=30)
        if len(result.stdout) > 1024 * 1024:
            raise ValueError('Remote metadata exceeds its declared limit.')
        return json.loads(result.stdout)

    @contextmanager
    def tunnel(self, address):
        ip = ipaddress.ip_address(address)
        if ip.version != 4 or not ip.is_private or ip.is_loopback:
            raise ValueError('Require the inspected private Docker IPv4 address.')
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(self.base + ['-o', 'ExitOnForwardFailure=yes',
                '-L', f'127.0.0.1:11435:{ip}:11434', '-N', self.target],
                stdout=subprocess.DEVNULL, stderr=errors)
            try:
                for _ in range(30):
                    if process.poll() is not None:
                        raise RuntimeError('Private SSH tunnel exited before readiness.')
                    try:
                        with socket.create_connection(('127.0.0.1', 11435), timeout=1):
                            break
                    except OSError:
                        time.sleep(.5)
                else:
                    raise TimeoutError('Private SSH tunnel did not become ready.')
                yield
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)


def health():
    with urlopen(HEALTH_URL, timeout=25) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError('Unexpected health-response size.')
    return json.loads(raw)


def validate_health(data, expected_sha):
    if (data.get('git_sha') != expected_sha or data.get('status') != 'ok'
            or data.get('demo_mode') is not False or data.get('graph_mode') != 'neo4j'
            or data.get('llm_mode') != 'live' or data.get('auth_db_mode') != 'postgresql'
            or data.get('llm_provider') != 'openai_compatible'
            or data.get('model', '').split(':')[0] != 'phi4-mini'
            or data.get('auth_enabled') is not True or data.get('openapi_enabled') is not False
            or data.get('maintenance_corpus_loaded') is not True
            or type(data.get('maintenance_record_count')) is not int
            or data['maintenance_record_count'] <= 0):
        raise ValueError('Require the exact healthy deployed revision and corpus.')


def private_server(metadata):
    if metadata.get('running') is not True or metadata.get('image') != 'ollama/ollama:0.9.6':
        raise ValueError('Require the existing pinned, running Ollama container.')
    if any(bindings for bindings in metadata.get('ports', {}).values()):
        raise ValueError('Ollama must have no published host ports.')
    if (metadata.get('memory_limit') != 4 * 1024**3
            or metadata.get('nano_cpus') != 2 * 10**9):
        raise ValueError('Require the documented existing model resource limits.')
    addresses = [network.get('IPAddress') for network in metadata['networks'].values()]
    if len(addresses) != 1:
        raise ValueError('Require one unambiguous existing model network.')
    ip = ipaddress.ip_address(addresses[0])
    if ip.version != 4 or not ip.is_private or ip.is_loopback:
        raise ValueError('Model address must be private Docker IPv4.')
    return str(ip)


def server_configuration(config, expected_sha):
    parsed = urlsplit(config['OPENAI_COMPAT_BASE_URL'])
    if (parsed.scheme != 'http' or parsed.hostname != 'halite-ollama'
            or parsed.port != 11434 or parsed.path.rstrip('/') != '/v1'
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or config.get('GIT_SHA') != expected_sha
            or config.get('LLM_PROVIDER') != 'openai_compatible'
            or not config.get('OPENAI_COMPAT_API_KEY')
            or config.get('GROQ_MODEL', '').split(':')[0] != 'phi4-mini'):
        raise ValueError('Require the deployed private phi4-mini configuration.')


@contextmanager
def model_token(value):
    previous = os.environ.get('HALITE_MODEL_API_KEY')
    os.environ['HALITE_MODEL_API_KEY'] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('HALITE_MODEL_API_KEY', None)
        else:
            os.environ['HALITE_MODEL_API_KEY'] = previous


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def measure(output, expected_sha, *, remote):
    if not re.fullmatch('[0-9a-f]{40}', expected_sha):
        raise ValueError('An exact lowercase 40-character revision is required.')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    status = {'complete': False, 'stage': 'public_preflight', 'source_sha': expected_sha,
              'timeout_seconds': 600,
              'measurement_role': 'staging_reference', 'm4_measurement': False}
    try:
        before = health()
        write(output / 'health-before.json', before)
        validate_health(before, expected_sha)
        status['stage'] = 'private_metadata'
        config = remote.read_json('docker', 'exec', 'halite-api', 'python', '-c', CONFIG_CODE)
        server_configuration(config, expected_sha)
        initial = remote.read_json('docker', 'inspect', '--format', INSPECT, 'halite-ollama')
        address = private_server(initial)
        safe = {key: initial[key] for key in ('id', 'image', 'restarts', 'memory_limit', 'nano_cpus')}
        provenance = {'source_sha': expected_sha, 'model_container': safe,
            'inference_location': 'Existing private halite-ollama container reached over staging SSH',
            'runner_location': 'GitHub Actions runner; see comparison manifest hardware',
            'timing_scope': 'Wall timings include SSH tunnel, network, queueing and model load.',
            'public_model_ports': False, 'database_writes': False,
            'model_pulls_or_configuration_changes': False, 'm4_measurement': False}
        write(output / 'server-provenance.json', provenance)
        status['stage'] = 'measurement'
        with remote.tunnel(address), model_token(config['OPENAI_COMPAT_API_KEY']):
            transport = Ollama(ENDPOINT, token=config['OPENAI_COMPAT_API_KEY'])
            tags = transport.request('/api/tags').get('models', [])
            requested = config['GROQ_MODEL']
            names = [row['name'] for row in tags if row.get('name') in
                     (requested, requested + ':latest')]
            if len(names) != 1:
                raise ValueError('Require one exact installed reference-model tag.')
            packet = Path(__file__).with_name('data') / 'model_prompts_2024_v1.json'
            # No injected client: manifest must accurately record real Ollama HTTP.
            result = compare(packet, names, output / 'comparison', endpoint=ENDPOINT,
                             role='staging_reference', timeout=600)
            status.update(n_attempts=result['n_attempts'], n_responses=result['n_responses'],
                          provider_errors=result['provider_errors'])
        status['stage'] = 'after_check'
        after = health()
        write(output / 'health-after.json', after)
        validate_health(after, expected_sha)
        if after['maintenance_record_count'] != before['maintenance_record_count']:
            raise ValueError('Corpus count changed during measurement; inspect before acceptance.')
        final = remote.read_json('docker', 'inspect', '--format', INSPECT, 'halite-ollama')
        private_server(final)
        write(output / 'server-after.json', {key: final[key] for key in
              ('id', 'image', 'restarts', 'memory_limit', 'nano_cpus')})
        if any(final[key] != initial[key] for key in ('id', 'restarts', 'image')):
            raise ValueError('Reference model container changed/restarted during measurement.')
        if not result['complete'] or result['n_attempts'] != 30 or result['provider_errors']:
            status['stage'] = 'attempts_failed'
            raise ValueError('Reference run contains incomplete/failed attempts; preserve them.')
        status.update(complete=True, stage='complete', n_attempts=result['n_attempts'],
                      n_responses=result['n_responses'], provider_errors=result['provider_errors'])
        return result
    except Exception as exc:
        status['error_type'] = type(exc).__name__
        raise
    finally:
        # Never serialize remote configuration, token, SSH keys or exception text.
        write(output / 'status.json', status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'revision', 'ssh-target', 'ssh-key', 'known-hosts'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        measure(args.output, args.revision,
                remote=SSH(args.ssh_target, args.ssh_key, args.known_hosts))
    except Exception as exc:
        raise SystemExit('Reference measurement failed: ' + type(exc).__name__) from None


if __name__ == '__main__':
    main()
