"""Test failure propagation without pulling or rewriting the real repository."""
import contextlib
import io
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import update_master_data as updater


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(updater.__file__).resolve().parent.parent
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)

    @patch.object(updater.subprocess, 'run')
    def test_pull_then_existing_converter(self, run):
        run.return_value = subprocess.CompletedProcess([], 0)
        updater.update(self.root)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], ['git', 'pull', '--ff-only'])
        self.assertEqual(run.call_args_list[1].args[0], [updater.sys.executable,
                         str(self.root / 'scripts' / 'gakumasu_diff_to_json.py'), '--strict'])
        self.assertTrue(all(call.kwargs == {'cwd': self.root} for call in run.call_args_list))

    @patch.object(updater.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1))
    def test_pull_failure_does_not_start_conversion(self, run):
        with self.assertRaisesRegex(RuntimeError, 'conversion was not started'):
            updater.update(self.root)
        self.assertEqual(run.call_count, 1)

    @patch.object(updater.subprocess, 'run', side_effect=FileNotFoundError('git'))
    def test_missing_git_does_not_start_conversion(self, run):
        with self.assertRaises(OSError):
            updater.update(self.root)
        self.assertEqual(run.call_count, 1)

    @patch.object(updater.subprocess, 'run')
    def test_converter_failure_is_reported(self, run):
        run.side_effect = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1)]
        with self.assertRaisesRegex(RuntimeError, 'JSON conversion failed'):
            updater.update(self.root)

    @patch.object(updater, 'update', side_effect=RuntimeError('failure'))
    def test_cli_failure_returns_nonzero(self, _):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(updater.main(), 1)


if __name__ == '__main__':
    unittest.main()
