"""Test snapshot copying without accessing GitHub or changing real orig/JSON."""
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import zipfile

import update_master_data as updater


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parent.parent / 'tools' / 'campus' / 'cache'
        self.temp = tempfile.TemporaryDirectory(prefix='yaml-copy-test-', dir=cache)
        self.root = Path(self.temp.name)
        self.orig = self.root / 'gakumasu-diff' / 'orig'
        self.orig.mkdir(parents=True)
        self.staging = self.root / 'staging'
        self.staging.mkdir()
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)
        self.temp.cleanup()

    def archive(self, entries):
        path = self.root / 'snapshot.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, value in entries.items():
                archive.writestr('repo-main/' + name, value)
        return path

    def test_copies_yaml_bytes_and_version_without_other_repository_files(self):
        self.orig.joinpath('Removed.yaml').write_bytes(b'old')
        translated = self.root / 'data.json'
        translated.write_bytes(b'local translation')
        raw_yaml = '- id: sample\n  name: 学園\u000b\n'.encode('utf-8')
        archive = self.archive({'gakumasu-diff/orig/Example.yaml': raw_yaml,
                                'gakumasu-diff/master-version.txt': b'version\n',
                                'data.json': b'remote translation',
                                'scripts/example.py': b'new code'})
        self.assertEqual(updater.copy_yaml_snapshot(archive, self.orig, self.staging), 1)
        self.assertEqual(self.orig.joinpath('Example.yaml').read_bytes(), raw_yaml)
        self.assertFalse(self.orig.joinpath('Removed.yaml').exists())
        self.assertEqual(self.orig.parent.joinpath('master-version.txt').read_bytes(), b'version\n')
        self.assertEqual(translated.read_bytes(), b'local translation')

    def test_empty_remote_snapshot_preserves_previous_yaml(self):
        previous = self.orig / 'Example.yaml'
        previous.write_bytes(b'previous')
        archive = self.archive({'README.md': b'no YAML'})
        with self.assertRaises(RuntimeError):
            updater.copy_yaml_snapshot(archive, self.orig, self.staging)
        self.assertEqual(previous.read_bytes(), b'previous')

    def test_invalid_archive_path_never_replaces_local_yaml(self):
        previous = self.orig / 'Example.yaml'
        previous.write_bytes(b'previous')
        archive = self.archive({'gakumasu-diff/orig/Example.yaml': b'new',
                                'gakumasu-diff/orig/../../escape.yaml': b'bad'})
        with self.assertRaises(RuntimeError):
            updater.copy_yaml_snapshot(archive, self.orig, self.staging)
        self.assertEqual(previous.read_bytes(), b'previous')
        self.assertFalse(self.root.joinpath('escape.yaml').exists())

    @patch.object(updater, 'remote_repository', return_value='owner/repo')
    @patch.object(updater.urllib.request, 'urlopen', side_effect=urllib.error.URLError('offline'))
    @patch.object(updater.subprocess, 'run')
    def test_download_failure_does_not_copy_or_run_converter(self, run, *_):
        previous = self.orig / 'Example.yaml'
        previous.write_bytes(b'previous')
        with self.assertRaises(urllib.error.URLError):
            updater.update(self.root)
        run.assert_not_called()
        self.assertEqual(previous.read_bytes(), b'previous')

    @patch.object(updater.subprocess, 'run')
    def test_origin_https_and_ssh_urls(self, run):
        for url in ['https://github.com/owner/repo.git', 'git@github.com:owner/repo.git',
                    'https://github.com/owner/repo']:
            run.return_value = subprocess.CompletedProcess([], 0, stdout=url, stderr='')
            self.assertEqual(updater.remote_repository(self.root), 'owner/repo')


if __name__ == '__main__':
    unittest.main()
