"""The read-only observer must never publish raw model logs or environment data."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

SPEC = importlib.util.spec_from_file_location(
    'model_progress_observer', Path(__file__).resolve().parents[2] / 'scripts/vm/model_progress.py')
observer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observer)


class ModelProgressObserverTests(unittest.TestCase):
    def test_extract_only_completed_chat_status_duration_and_time(self):
        value = ('server environment TOKEN=never-publish\n'
                 '[GIN] 2026/11/22 - 04:58:00 | 200 | 1m2.34s | 172.18.0.1 | POST "/api/chat"\n'
                 '[GIN] 2026/11/22 - 04:59:00 | 500 | 12.3ms | 172.18.0.1 | POST "/api/chat"\n'
                 '[GIN] 2026/11/22 - 04:59:01 | 200 | 1ms | 172.18.0.1 | GET "/api/tags"')
        parsed = observer.parse_chat_lines(value)
        self.assertEqual(parsed, [
            {'server_log_time': '2026/11/22 - 04:58:00', 'status': 200, 'duration': '1m2.34s'},
            {'server_log_time': '2026/11/22 - 04:59:00', 'status': 500, 'duration': '12.3ms'}])
        self.assertNotIn('never-publish', json.dumps(parsed))
        self.assertNotIn('172.18', json.dumps(parsed))

    def test_refuse_extra_or_unrecognised_log_fields(self):
        for line in [
            '[GIN] 2026/11/22 - 04:58:00 | 200 | TOKEN=secret | 172.18.0.1 | POST "/api/chat"',
            '[GIN] 2026/11/22 - 04:58:00 | 200 | 1s | 172.18.0.1 | POST "/api/chat?token=secret"',
            '[GIN] 2026/11/22 - 04:58:00 | 200 | 1s | 172.18.0.1 | POST "/api/chat" token=secret',
        ]:
            with self.subTest(line=line):
                self.assertEqual(observer.parse_chat_lines(line), [])

    def test_snapshot_uses_read_commands_and_whitelists_every_output(self):
        commands = []
        def run(args):
            commands.append(args)
            if args[1] == 'inspect':
                return SimpleNamespace(stdout=json.dumps({'id': 'example', 'running': True, 'oom_killed': False,
                    'restarts': 0, 'memory_limit': 4294967296, 'nano_cpus': 2000000000, 'env': 'secret'}))
            if args[1] == 'stats':
                return SimpleNamespace(stdout=json.dumps({'CPUPerc': '199.00%', 'MemUsage': '3GiB / 4GiB',
                    'MemPerc': '75%', 'PIDs': '12', 'unexpected': 'secret'}))
            return SimpleNamespace(stdout='token=secret', stderr='some other sensitive log')
        result = observer.snapshot(run)
        self.assertEqual([args[1] for args in commands], ['inspect', 'stats', 'logs'])
        self.assertIs(result['writes_or_inference'], False)
        self.assertEqual(result['recent_chat_completions'], [])
        self.assertNotIn('secret', json.dumps(result))
        self.assertNotIn('sensitive', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
