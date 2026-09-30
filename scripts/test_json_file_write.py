"""Exercise real Windows mapped-file failures and preservation of existing JSON."""
import contextlib
import io
import json
import mmap
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import gakumasu_diff_to_json as converter


class JsonWriteTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parent.parent / 'tools' / 'campus' / 'cache'
        self.temp = tempfile.TemporaryDirectory(prefix='json-write-test-', dir=cache)
        self.folder = Path(self.temp.name)
        self.target = self.folder / 'Example.json'
        self.old = {'text': '旧内容'}
        self.new = {'text': '新内容', 'rows': [1, 2]}
        self.target.write_bytes(json.dumps(self.old, ensure_ascii=False, indent=4).encode('utf-8'))

    def tearDown(self):
        self.temp.cleanup()

    def assert_no_temporary_files(self):
        self.assertEqual([path.name for path in self.folder.iterdir()], ['Example.json'])

    def test_same_content_preserves_timestamp_without_replacement(self):
        timestamp = self.target.stat().st_mtime_ns
        with patch.object(Path, 'replace', side_effect=AssertionError('unchanged JSON must not be replaced')):
            converter.write_json_file(self.target, self.old)
        self.assertEqual(self.target.stat().st_mtime_ns, timestamp)
        self.assert_no_temporary_files()

    def test_new_content_matches_original_serialization(self):
        converter.write_json_file(self.target, self.new)
        self.assertEqual(self.target.read_bytes(), json.dumps(self.new, ensure_ascii=False, indent=4).encode('utf-8'))
        self.assert_no_temporary_files()

    def test_serialization_failure_preserves_old_json(self):
        before = self.target.read_bytes()
        with self.assertRaises(TypeError):
            converter.write_json_file(self.target, {'unsupported': object()})
        self.assertEqual(self.target.read_bytes(), before)
        self.assert_no_temporary_files()

    def test_persistent_replacement_failure_preserves_old_json(self):
        before = self.target.read_bytes()
        error = PermissionError('persistent lock')
        error.winerror = 5
        with patch.object(Path, 'replace', side_effect=error), patch.object(converter.time, 'monotonic', side_effect=[0, 4]):
            with self.assertRaises(PermissionError):
                converter.write_json_file(self.target, self.new)
        self.assertEqual(self.target.read_bytes(), before)
        self.assert_no_temporary_files()

    @unittest.skipUnless(os.name == 'nt', 'Windows mapped-file behavior')
    def test_unchanged_json_succeeds_while_mapping_remains_open(self):
        with self.target.open('rb') as reader, mmap.mmap(reader.fileno(), 0, access=mmap.ACCESS_READ):
            with self.assertRaises(OSError) as caught:
                self.target.open('w').close()
            self.assertEqual(caught.exception.errno, 22)
            converter.write_json_file(self.target, self.old)
        self.assertEqual(json.loads(self.target.read_text(encoding='utf-8')), self.old)
        self.assert_no_temporary_files()

    @unittest.skipUnless(os.name == 'nt', 'Windows mapped-file behavior')
    def test_changed_json_waits_until_actual_mapping_closes(self):
        reader = self.target.open('rb')
        mapping = mmap.mmap(reader.fileno(), 0, access=mmap.ACCESS_READ)

        def release():
            time.sleep(0.2)
            mapping.close()
            reader.close()

        thread = threading.Thread(target=release)
        thread.start()
        try:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                converter.write_json_file(self.target, self.new)
            self.assertIn('Windows', output.getvalue())
        finally:
            thread.join()
        self.assertEqual(json.loads(self.target.read_text(encoding='utf-8')), self.new)
        self.assert_no_temporary_files()


if __name__ == '__main__':
    unittest.main()
