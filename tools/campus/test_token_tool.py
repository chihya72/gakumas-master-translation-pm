"""Credential boundary tests; all GitHub writes are mocked."""
import base64
import json
from pathlib import Path
import subprocess
import tkinter as tk
import unittest
from unittest.mock import patch

import campus_token_tool as tool
import read_android_account as account
import schema_from_device as device_schema


def remote_schema(content=b'old schema\n'):
    return json.dumps({
        'type': 'file', 'encoding': 'base64', 'sha': 'a' * 40,
        'content': base64.b64encode(content).decode('ascii'),
    }).encode()


class TokenTests(unittest.TestCase):
    def test_endpoint_rejects_commands_and_invalid_ports(self):
        for host, port in [('127.0.0.1;anything', '16448'), ('127.0.0.1', '0'),
                           ('127.0.0.1', '65536'), ('127.0.0.1', 'abc')]:
            with self.assertRaises(tool.ToolError):
                tool.endpoint(host, port)
        self.assertEqual(tool.endpoint('127.0.0.1', '16448'), '127.0.0.1:16448')
        self.assertEqual(tool.endpoint('::1', '5555'), '[::1]:5555')

    def test_repo_rejects_arguments(self):
        with self.assertRaises(tool.ToolError):
            tool.repository('owner/repo --env production')

    @patch.object(tool, 'find_gh', return_value='gh.exe')
    @patch.object(tool, 'build_schema', return_value=b'new schema\n')
    @patch.object(tool.subprocess, 'run')
    def test_upload_writes_secret_before_committing_schema(self, run, build, _):
        run.side_effect = [subprocess.CompletedProcess([], 0, data, b'')
                           for data in (b'', remote_schema(), b'', b'')]
        result = tool.publish('PRIVATE_TEST_TOKEN', 'owner/repo', 'adb.exe', 'device')
        self.assertIn('Schema 提交到 main', result)
        self.assertEqual(run.call_count, 4)
        self.assertEqual(build.call_args.args[:2], ('adb.exe', 'device'))
        self.assertIn('?ref=main', run.call_args_list[1].args[0][-1])
        call = run.call_args_list[2]
        self.assertEqual(call.args[0], ['gh.exe', 'secret', 'set', 'CAMPUS_REFRESH_TOKEN',
                                       '--app', 'actions', '--repo', 'owner/repo'])
        self.assertEqual(call.kwargs['input'], b'PRIVATE_TEST_TOKEN')
        self.assertNotIn('PRIVATE_TEST_TOKEN', repr(call.args))
        self.assertNotIn('shell', call.kwargs)
        commit = run.call_args_list[3]
        self.assertIn('PUT', commit.args[0])
        self.assertIn(f'repos/owner/repo/contents/{tool.SCHEMA_PATH}', commit.args[0])
        body = json.loads(commit.kwargs['input'])
        self.assertEqual(body['branch'], 'main')
        self.assertEqual(body['sha'], 'a' * 40)
        self.assertEqual(base64.b64decode(body['content']), b'new schema\n')

    @patch.object(tool, 'find_gh', return_value='gh.exe')
    @patch.object(tool, 'build_schema', return_value=b'existing schema\n')
    @patch.object(tool, 'run_native', side_effect=[b'', remote_schema(b'existing schema\r\n'), b''])
    def test_identical_schema_updates_secret_without_new_commit(self, run, *_):
        result = tool.publish('PRIVATE_TEST_TOKEN', 'owner/repo', 'adb.exe', 'device')
        self.assertIn('Schema 已一致', result)
        self.assertEqual(run.call_count, 3)

    @patch.object(tool, 'find_gh', return_value='gh.exe')
    @patch.object(tool, 'build_schema', side_effect=ValueError('invalid schema'))
    @patch.object(tool, 'run_native')
    def test_schema_failure_stops_before_secret_write(self, run, *_):
        with self.assertRaisesRegex(tool.ToolError, 'invalid schema'):
            tool.publish('PRIVATE_TEST_TOKEN', 'owner/repo', 'adb.exe', 'device')
        self.assertEqual(run.call_count, 1)

    @patch.object(tool, 'find_gh', return_value='gh.exe')
    @patch.object(tool, 'build_schema', return_value=b'new schema\n')
    @patch.object(tool.subprocess, 'run')
    def test_commit_failure_reports_partial_success(self, run, *_):
        run.side_effect = [subprocess.CompletedProcess([], 0, data, b'')
                           for data in (b'', remote_schema(), b'')] + [
                               subprocess.CompletedProcess([], 1, b'', b'PRIVATE_RESPONSE')]
        with self.assertRaisesRegex(tool.ToolError, 'Secret 已更新，但 Schema 提交未获确认') as caught:
            tool.publish('PRIVATE_TEST_TOKEN', 'owner/repo', 'adb.exe', 'device')
        self.assertNotIn('PRIVATE', str(caught.exception))

    @patch.object(tool, 'find_gh', return_value='gh.exe')
    @patch.object(tool.subprocess, 'run')
    def test_failed_login_never_attempts_upload(self, run, _):
        run.return_value = subprocess.CompletedProcess([], 1, b'PRIVATE_RESPONSE', b'PRIVATE_ERROR')
        with self.assertRaises(tool.ToolError) as caught:
            tool.publish('PRIVATE_TEST_TOKEN', 'owner/repo', 'adb.exe', 'device')
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('PRIVATE', str(caught.exception))

    @patch.object(tool, 'find_gh', return_value='gh.exe')
    @patch.object(tool, 'build_schema', return_value=b'new schema\n')
    @patch.object(tool.subprocess, 'run')
    def test_failed_upload_redacts_subprocess_output(self, run, *_):
        run.side_effect = [subprocess.CompletedProcess([], 0, b'', b''),
                           subprocess.CompletedProcess([], 0, remote_schema(), b''),
                           subprocess.CompletedProcess([], 1, b'PRIVATE_RESPONSE', b'PRIVATE_TOKEN')]
        with self.assertRaises(tool.ToolError) as caught:
            tool.publish('PRIVATE_TEST_TOKEN', 'owner/repo', 'adb.exe', 'device')
        self.assertNotIn('PRIVATE', str(caught.exception))
        self.assertEqual(run.call_count, 3)

    def test_installed_apks_searches_split_package_directory(self):
        folder = f'/data/app/~~install==/{account.PACKAGE}-client_123=='
        listings = {
            '/data/app': [('~~install==', 0)],
            '/data/app/~~install==': [(folder.rsplit('/', 1)[1], 0)],
            folder: [('split_UnityDataAssetPack.apk', 1), ('split_config.arm64_v8a.apk', 1),
                     ('base.apk', 1), ('oat', 0)],
        }
        with patch.object(account, 'directory_entries', side_effect=lambda _, path: listings[path]):
            self.assertEqual(device_schema.installed_apks('device'),
                             [folder + '/' + name for name in
                              ('base.apk', 'split_config.arm64_v8a.apk', 'split_UnityDataAssetPack.apk')])

    @patch.object(tool.subprocess, 'run')
    def test_timeout_redacts_command_input(self, run):
        run.side_effect = subprocess.TimeoutExpired(['PRIVATE_TOKEN'], 60, output=b'PRIVATE_BODY')
        with self.assertRaises(tool.ToolError) as caught:
            tool.run_native(['gh.exe'], data=b'PRIVATE_TOKEN')
        self.assertNotIn('PRIVATE', str(caught.exception))

    @patch.object(tool, 'connect_device')
    @patch.object(account, 'auth_files', return_value=['account.xml'])
    @patch.object(account, 'read_account', return_value=b'ENCRYPTED:private')
    @patch.object(account, 'decrypt_on_device', return_value='PRIVATE_TOKEN')
    @patch.object(account, 'validate', side_effect=RuntimeError('Firebase validation rejected; HTTP 400.'))
    @patch.object(account, 'protect')
    def test_expired_token_does_not_replace_saved_credential(self, protect, *_):
        with self.assertRaises(tool.ToolError) as caught:
            tool.recover('adb.exe', '127.0.0.1:16448')
        protect.assert_not_called()
        self.assertIn('重新登录', str(caught.exception))

    @patch.object(tool, 'connect_device', side_effect=RuntimeError('PRIVATE_ACCOUNT_XML'))
    def test_unexpected_device_errors_are_redacted(self, _):
        with self.assertRaises(tool.ToolError) as caught:
            tool.recover('adb.exe', '127.0.0.1:16448')
        self.assertNotIn('PRIVATE', str(caught.exception))

    def test_plaintext_auth_and_xml_entity_rejection(self):
        state = json.dumps({'refresh_token': 'PRIVATE_TEST_TOKEN'})
        user = json.dumps({'cachedTokenState': state})
        xml = ('<map><string name="com.google.firebase.auth.FIREBASE_USER">' + user + '</string></map>').encode()
        self.assertEqual(account.extract_token(xml), 'PRIVATE_TEST_TOKEN')
        with self.assertRaises(RuntimeError):
            account.extract_token(b'<!DOCTYPE map><map/>')

    def test_distributed_helper_is_dex(self):
        data = base64.b64decode((Path(__file__).parent / 'account_helper.b64').read_bytes())
        self.assertTrue(data.startswith(b'dex\n'))


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = tool.TokenWindow(self.root)

    def tearDown(self):
        self.window.close()

    def test_input_change_invalidates_upload(self):
        self.window.token = 'PRIVATE_TEST_TOKEN'
        self.window.set_busy(False)
        self.assertEqual(str(self.window.upload_button['state']), 'normal')
        self.window.repo.set('other/repository')
        self.assertIsNone(self.window.token)
        self.assertEqual(str(self.window.upload_button['state']), 'disabled')

    def test_read_completion_does_not_publish(self):
        with patch.object(tool, 'publish') as publish:
            self.window.events.put(('recovered', 'PRIVATE_TEST_TOKEN'))
            self.window.poll()
            publish.assert_not_called()
            self.assertEqual(str(self.window.upload_button['state']), 'normal')
            self.assertNotIn('PRIVATE_TEST_TOKEN', self.window.status.get())

    def test_upload_button_uses_the_account_device(self):
        self.window.adb.set('test-adb.exe')
        self.window.token = 'PRIVATE_TEST_TOKEN'
        self.window.set_busy(False)
        with patch.object(self.window, 'start') as start, patch.object(tool, 'publish') as publish:
            self.window.upload_button.invoke()
            kind, action = start.call_args.args
            self.assertEqual(kind, 'published')
            action(None)
            publish.assert_called_once_with('PRIVATE_TEST_TOKEN', tool.DEFAULT_REPO,
                                            'test-adb.exe', '127.0.0.1:16448', None)

    def test_success_clears_token_and_failure_keeps_retry_available(self):
        self.window.token = 'PRIVATE_TEST_TOKEN'
        self.window.events.put(('error', '模拟上传失败'))
        self.window.poll()
        self.assertEqual(str(self.window.upload_button['state']), 'normal')
        self.window.events.put(('published', 'owner/repo'))
        self.window.poll()
        self.assertIsNone(self.window.token)
        self.assertEqual(str(self.window.upload_button['state']), 'disabled')

    def test_close_waits_for_device_cleanup(self):
        self.window.set_busy(True)
        self.window.close()
        self.assertTrue(self.root.winfo_exists())
        self.window.set_busy(False)


if __name__ == '__main__':
    unittest.main()
