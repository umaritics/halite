"""Read-only, secret-free Ollama activity snapshot; runs over SSH on the VM."""
from datetime import datetime, timezone
import json
import re
import subprocess

CHAT_LINE = re.compile(
    r'^\[GIN\]\s+(\d{4}/\d{2}/\d{2}\s+-\s+\d{2}:\d{2}:\d{2})\s*'
    r'\|\s*(\d{3})\s*\|\s*([0-9.µumhns]+)\s*\|[^|]+\|\s*POST\s+"/api/chat"\s*$'
)


def parse_chat_lines(value):
    matches = []
    for line in value.splitlines():
        match = CHAT_LINE.fullmatch(line.strip())
        if match:
            timestamp, status, duration = match.groups()
            matches.append({'server_log_time': timestamp, 'status': int(status),
                            'duration': duration})
    return matches


def command(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=20)


def snapshot(run=command):
    metadata = json.loads(run([
        'docker', 'inspect', '--format',
        '{"id":{{json .Id}},"running":{{json .State.Running}},'
        '"oom_killed":{{json .State.OOMKilled}},"restarts":{{json .RestartCount}},'
        '"memory_limit":{{json .HostConfig.Memory}},"nano_cpus":{{json .HostConfig.NanoCpus}}}',
        'halite-ollama']).stdout)
    stats = json.loads(run(['docker', 'stats', '--no-stream', '--format', '{{json .}}', 'halite-ollama']).stdout)
    logs = run(['docker', 'logs', '--tail', '2000', 'halite-ollama'])
    return {'schema': 'halite-model-progress-v1',
            'observed_at_utc': datetime.now(timezone.utc).isoformat(),
            'container': {key: metadata[key] for key in
                          ['id', 'running', 'oom_killed', 'restarts', 'memory_limit', 'nano_cpus']},
            'resources': {key: stats[key] for key in ['CPUPerc', 'MemUsage', 'MemPerc', 'PIDs']},
            'recent_chat_completions': parse_chat_lines(logs.stdout + '\n' + logs.stderr),
            'log_tail_limit': 2000, 'writes_or_inference': False,
            'interpretation': 'Recent server activity only; requests cannot be attributed to a particular research case. Missing parsed lines do not prove a stopped job.'}


if __name__ == '__main__':
    try:
        print(json.dumps(snapshot(), indent=2))
    except Exception as error:
        print(json.dumps({'schema': 'halite-model-progress-v1', 'failed': True,
                          'error_type': type(error).__name__}))
        raise SystemExit(1) from None
