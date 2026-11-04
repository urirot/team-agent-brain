"""Tests for tools/brain.py against the sample notes in people/. Run: python3 -m unittest discover tools"""
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent / 'brain.py'
sys.path.insert(0, str(TOOL.parent))
import brain  # noqa: E402


def run(*args, stdin='', env=None):
    return subprocess.run([sys.executable, str(TOOL), *args], input=stdin, capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, timeout=60)


def context(out):
    return json.loads(out)['hookSpecificOutput']['additionalContext'] if out.strip() else ''


class Notes(unittest.TestCase):
    def test_sample_notes_pass_check(self):
        r = run('check')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_parses_status_abstract_links_and_cites(self):
        d = brain.parse_note(brain.ROOT / 'people/sam/dashboard-queue-leak/analysis.md')
        self.assertTrue(d['status'].startswith('shipped'))
        self.assertIn('whole transcript', d['abstract'])
        self.assertIn('people/alex/api-pod-oom/analysis.md', d['links'])
        self.assertIn('api/dashboard_stream.py', d['cites'])


class Ranking(unittest.TestCase):
    def setUp(self):
        self.index = brain.build()

    def top(self, query):
        rows = brain.best_per_folder(brain.rank(self.index, query, limit=20), 5)
        return [r[2]['folder'] for r in rows]

    def test_the_task_text_finds_the_note(self):
        self.assertEqual(self.top('our API pods keep running out of memory')[0], 'people/sam/dashboard-queue-leak')
        self.assertEqual(self.top('the login test is flaky in CI')[0], 'people/jo/flaky-login-e2e')

    def test_superseded_note_ranks_below_its_replacement(self):
        top = self.top('API pod out of memory')
        self.assertLess(top.index('people/sam/dashboard-queue-leak'), top.index('people/alex/api-pod-oom'))

    def test_an_issue_number_finds_the_note_about_it(self):
        self.assertEqual(self.top('look at #398')[0], 'people/sam/dashboard-queue-leak')


class Hooks(unittest.TestCase):
    def test_prompt_hook_brings_matching_notes_and_their_lessons(self):
        text = context(run('hook', 'prompt', stdin=json.dumps({'prompt': 'API memory keeps climbing'})).stdout)
        self.assertIn('people/sam/dashboard-queue-leak', text)
        self.assertIn('Send a live screen only what it shows', text)

    def test_prompt_hook_is_silent_without_content(self):
        for prompt in ('yes', 'continue', 'ok do it'):
            self.assertEqual(run('hook', 'prompt', stdin=json.dumps({'prompt': prompt})).stdout, '')

    def test_file_hook_names_citing_notes_once_per_session(self):
        payload = json.dumps({'session_id': 'test-%d' % os.getpid(),
                              'tool_input': {'file_path': '/src/app/api/dashboard_stream.py'}})
        first = context(run('hook', 'file', stdin=payload).stdout)
        self.assertIn('2 notes cite dashboard_stream.py', first)
        self.assertEqual(run('hook', 'file', stdin=payload).stdout, '')
        (brain.INDEX_DIR / ('seen-test-%d.json' % os.getpid())).unlink(missing_ok=True)

    def test_file_hook_ignores_files_nobody_cites(self):
        payload = json.dumps({'session_id': 'x', 'tool_input': {'file_path': '/src/app/unrelated.py'}})
        self.assertEqual(run('hook', 'file', stdin=payload).stdout, '')

    def test_session_start_fits_under_the_cap(self):
        text = context(run('hook', 'session-start', env={'BRAIN_AUTOPULL': '0'}).stdout)
        self.assertIn('people/jo/flaky-login-e2e', text)
        self.assertIn('### Lessons', text)
        self.assertLessEqual(len(text), brain.HOOK_CAP)

    def test_cursor_format_is_flat(self):
        out = run('hook', 'session-start', '--cursor', env={'BRAIN_AUTOPULL': '0'}).stdout
        self.assertIn('additional_context', json.loads(out))

    def test_push_is_off_unless_opted_in(self):
        r = run('hook', 'stop', env={'BRAIN_AUTOPUSH': '0', 'BRAIN_USER': 'alex'})
        self.assertEqual((r.returncode, r.stdout), (0, ''))

    def test_a_broken_hook_never_fails_the_session(self):
        r = run('hook', 'prompt', stdin='not json')
        self.assertEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
