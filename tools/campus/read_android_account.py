"""Read the user's game Firebase Auth state through ADB sync, without a shell."""
import argparse
import base64
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import socket
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

PACKAGE = 'com.bandainamcoent.idolmaster_gakuen'
PROJECT = '544792984478'
ENDPOINT = 'https://securetoken.googleapis.com/v1/token?key=AIzaSyCe_vKRW5Pc0rTXFksur-ZCDb_kRCxNhng'
FOLDER = '/data/data/' + PACKAGE + '/shared_prefs'
MAX_BYTES = 1024 * 1024


def exact(connection, count):
    if count < 0 or count > MAX_BYTES:
        raise RuntimeError('Invalid ADB response length.')
    chunks = bytearray()
    while len(chunks) < count:
        block = connection.recv(count - len(chunks))
        if not block:
            raise RuntimeError('ADB connection closed.')
        chunks.extend(block)
    return bytes(chunks)


def service(connection, name):
    data = name.encode('utf-8')
    connection.sendall(f'{len(data):04x}'.encode() + data)
    if exact(connection, 4) != b'OKAY':
        size = int(exact(connection, 4), 16)
        exact(connection, size)  # Do not print server responses.
        raise RuntimeError('ADB service rejected; check device connection and access.')


def sync_connection(device):
    connection = socket.create_connection(('127.0.0.1', 5037), timeout=15)
    try:
        service(connection, 'host:transport:' + device)
        service(connection, 'sync:')
        return connection
    except Exception:
        connection.close()
        raise


def request(connection, operation, path):
    data = path.encode('utf-8')
    connection.sendall(operation + struct.pack('<I', len(data)) + data)


def auth_files(device):
    names = []
    with sync_connection(device) as connection:
        request(connection, b'LIST', FOLDER)
        while True:
            kind, value = struct.unpack('<4sI', exact(connection, 8))
            if kind == b'DONE':
                return names
            if kind == b'FAIL':
                exact(connection, value)
                raise RuntimeError('Game preferences directory cannot be read.')
            if kind != b'DENT':
                raise RuntimeError('Unexpected ADB directory response.')
            size, _, length = struct.unpack('<III', exact(connection, 12))
            name = exact(connection, length).decode('utf-8')
            if name.startswith('com.google.firebase.auth.api.Store.') and name.endswith('.xml'):
                if '/' in name or '\\' in name or size > MAX_BYTES:
                    raise RuntimeError('Invalid Firebase Auth file entry.')
                names.append(name)


def read_path(device, path):
    result = bytearray()
    with sync_connection(device) as connection:
        request(connection, b'RECV', path)
        while True:
            kind, length = struct.unpack('<4sI', exact(connection, 8))
            if kind == b'DONE':
                return bytes(result)
            if kind == b'FAIL':
                exact(connection, length)
                raise RuntimeError('Firebase Auth file cannot be read.')
            if kind != b'DATA' or len(result) + length > MAX_BYTES:
                raise RuntimeError('Invalid Firebase Auth transfer.')
            result.extend(exact(connection, length))


def read_account(device, name):
    return read_path(device, FOLDER + '/' + name)


def device_command(device, command):
    result = bytearray()
    with socket.create_connection(('127.0.0.1', 5037), timeout=20) as connection:
        service(connection, 'host:transport:' + device)
        service(connection, 'exec:' + command)
        while True:
            block = connection.recv(65536)
            if not block:
                return bytes(result)
            if len(result) + len(block) > MAX_BYTES:
                raise RuntimeError('Device helper response exceeds limit.')
            result.extend(block)


def decrypt_on_device(device, name):
    uid = None
    for line in read_path(device, '/data/system/packages.list').decode('utf-8').splitlines():
        columns = line.split()
        if columns and columns[0] == PACKAGE:
            uid = int(columns[1])
    if uid is None or not 10000 <= uid <= 99999:
        raise RuntimeError('Game application UID cannot be determined.')
    persistence_key = name[len('com.google.firebase.auth.api.Store.'):-len('.xml')]
    expected = 'W0RFRkFVTFRd+MTo1NDQ3OTI5ODQ0Nzg6YW5kcm9pZDo5MTI0YzBjMmZiOTJhMjM3ODBiNDhm'
    if persistence_key != expected:
        raise RuntimeError('Device helper supports only the confirmed game Firebase app.')
    # The distributed helper contains code only, never account data or keys.
    bundle = Path(__file__).parent / 'account_helper.b64'
    if not bundle.is_file():
        raise RuntimeError('Distributed device helper is missing.')
    data = base64.b64decode(bundle.read_bytes(), validate=False)
    if not data.startswith(b'dex\n') or len(data) > MAX_BYTES:
        raise RuntimeError('Invalid device helper.')
    remote = '/data/local/tmp/gakumas-campus-account-helper.dex'
    with sync_connection(device) as connection:
        request(connection, b'SEND', remote + ',420')  # 0644; readable by the target UID.
        for offset in range(0, len(data), 65536):
            block = data[offset:offset + 65536]
            connection.sendall(b'DATA' + struct.pack('<I', len(block)) + block)
        connection.sendall(b'DONE' + struct.pack('<I', int(time.time())))
        kind, length = struct.unpack('<4sI', exact(connection, 8))
        if kind != b'OKAY':
            if kind == b'FAIL':
                exact(connection, length)
            raise RuntimeError('Temporary device helper upload failed.')
    try:
        # Device-side shell execution was explicitly authorized by the user.
        command = (f'CLASSPATH={remote} /system/bin/app_process /data/local/tmp '
                   f'CampusAccountDecryptor {uid} {persistence_key}')
        output = device_command(device, command)
        marker = b'CAMPUS_TOKEN:'
        if marker not in output:
            error_marker = b'CAMPUS_ERROR:'
            reason = output.split(error_marker, 1)[-1].strip() if error_marker in output else b''
            if reason and len(reason) < 100 and all(chr(value).isalnum() or chr(value) in '_/' for value in reason):
                raise RuntimeError('Device decryption failed: ' + reason.decode('ascii'))
            raise RuntimeError('Device decryption failed; response content hidden.')
        return output.split(marker, 1)[1].decode('utf-8').strip()
    finally:
        # Remove only the file uploaded by this helper; never touch game files.
        cleanup = device_command(device, '/system/bin/rm ' + remote + ' && /system/bin/echo CAMPUS_HELPER_REMOVED')
        if b'CAMPUS_HELPER_REMOVED' not in cleanup:
            raise RuntimeError('Temporary device helper cleanup failed.')


def extract_token(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise RuntimeError('XML document declarations are not supported.')
    root = ET.fromstring(data)
    if root.tag != 'map':
        raise RuntimeError('Expected Android SharedPreferences XML.')
    users = [entry for entry in root.findall('string')
             if entry.get('name') == 'com.google.firebase.auth.FIREBASE_USER']
    tokens = set()
    for entry in users:
        if (entry.text or '').startswith('ENCRYPTED:'):
            raise RuntimeError('Auth state is encrypted; Android Keystore decryption is required.')
        user = json.loads(entry.text)
        state = json.loads(user['cachedTokenState'])
        token = state.get('refresh_token')
        if isinstance(token, str) and token.strip():
            tokens.add(token)
    if len(tokens) != 1:
        raise RuntimeError('Expected one cached Firebase Auth user.')
    return tokens.pop()


def validate(token):
    body = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': token}).encode()
    headers = {'Content-Type': 'application/x-www-form-urlencoded',
               'X-Android-Package': PACKAGE,
               'X-Android-Cert': 'D05C4DC398804FEB2ADF30E8854500D2834EAFED'}
    request_object = urllib.request.Request(ENDPOINT, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request_object, timeout=20) as response:
            result = json.loads(response.read(MAX_BYTES))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'Firebase validation rejected; HTTP {error.code}.') from None
    if (str(result.get('project_id')) != PROJECT or not result.get('id_token')
            or not result.get('refresh_token')):
        raise RuntimeError('Firebase response does not match the game project.')
    return result['refresh_token']


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def protect(token):
    data = token.encode('utf-8')
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), buffer)
    target = Blob()
    function = ctypes.windll.crypt32.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.POINTER(Blob),
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), 'Campus Firebase account', None, None, None, 1, ctypes.byref(target)):
        raise RuntimeError('Windows credential encryption failed.')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.memset(buffer, 0, len(data))
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(target.data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    parser.add_argument('--decrypt-on-device', action='store_true',
                        help='Run the prepared helper on the original device to access Android Keystore.')
    options = parser.parse_args()
    names = auth_files(options.device)
    if len(names) != 1:
        raise RuntimeError('Expected one Firebase Auth store; inspect device preferences first.')
    try:
        if options.decrypt_on_device:
            token = decrypt_on_device(options.device, names[0])
        else:
            token = extract_token(read_account(options.device, names[0]))
    except (KeyError, ValueError, ET.ParseError, TypeError):
        raise RuntimeError('Unsupported Firebase Auth state; no file contents printed.') from None
    token = validate(token)
    destination = Path(__file__).parent / 'cache' / 'firebase-refresh-token.dpapi'
    if not destination.parent.is_dir():
        raise RuntimeError('Existing campus cache directory is missing.')
    destination.write_bytes(protect(token))
    print(json.dumps({'firebase_validated': True, 'game_project': PROJECT,
                      'saved_encrypted': str(destination)}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        print(str(error))
        raise SystemExit(1)
    except Exception:
        print('Account extraction failed. No credentials or response bodies were printed.')
        raise SystemExit(1)
