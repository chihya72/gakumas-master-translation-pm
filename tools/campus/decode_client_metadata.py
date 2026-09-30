"""Decode IL2CPP metadata from a read-only APK copy for schema extraction.

Metadata XOR mask discovery follows vilebbit/campus-meta (AGPL-3.0).
Only local cache copies are read or written; the installed client is untouched.
"""
from pathlib import Path
import struct


def main():
    cache = Path(__file__).parent / 'cache'
    metadata = (cache / 'global-metadata.dat').read_bytes()
    signature = bytes.fromhex('AF1BB1FA')
    if metadata[:4] != signature:
        native = (cache / 'libil2cpp.so').read_bytes()
        prefix = bytes(a ^ b for a, b in zip(metadata[:4], signature))
        candidates = []
        start = 0
        while True:
            offset = native.find(prefix, start)
            if offset < 0:
                break
            mask = native[offset:offset + 128]
            if len(mask) == 128:
                header = bytes(b ^ mask[i & 127] for i, b in enumerate(metadata[:256]))
                version = struct.unpack_from('<I', header, 4)[0]
                if 24 <= version <= 40:
                    candidates.append(mask)
            start = offset + 1
        if len(candidates) != 1:
            raise RuntimeError(f'Expected one metadata mask, found {len(candidates)}')
        mask = candidates[0]
        metadata = bytes(b ^ mask[i & 127] for i, b in enumerate(metadata))
    (cache / 'global-metadata-de.dat').write_bytes(metadata)
    print(f'Metadata version={struct.unpack_from("<I", metadata, 4)[0]}; decoded cache copy ready')


if __name__ == '__main__':
    main()
