"""Read-only integrity of explicitly selected copied roots; never replay work."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat

from verification_records import verify_record


def regular(path, *, directory=False):
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or path.is_symlink() or (not directory and info.st_nlink != 1):
        raise ValueError('nonregular transfer object: ' + str(path))
    return info


def pin(path):
    regular(path)
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while raw := stream.read(256 * 1024):
            digest.update(raw)
            size += len(raw)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def verify(root, expected_closure_sha256=None):
    root = root.absolute()
    for parent in (root, *root.parents):
        regular(parent, directory=True)
    marker = root / 'root-closed.json'
    if regular(marker).st_size > 256 * 1024:
        raise ValueError('closure marker too large')
    closure_pin = pin(marker)
    if expected_closure_sha256 is not None and (
            not re.fullmatch('[0-9a-f]{64}', expected_closure_sha256)
            or closure_pin['sha256'] != expected_closure_sha256):
        raise ValueError('external source closure hash mismatch')
    closure = json.loads(marker.read_bytes())
    if closure.get('format') == 'verification-records-closure-v1':
        record = verify_record(root)
        status, kind = record['status'], 'EvidenceStore'
    else:
        if closure.get('status') not in ('complete', 'failed') or closure.get('immutable') is not True:
            raise ValueError('invalid model closure status')
        files = closure['files']
        if type(files) is not dict or not files or len(files) > 31:
            raise ValueError('invalid model inventory')
        if {p.name for p in root.iterdir()} != set(files) | {'root-closed.json'}:
            raise ValueError('copied root file set differs from closure')
        total = 0
        for name, expected in files.items():
            if Path(name).name != name or not re.fullmatch('[A-Za-z0-9_.-]+', name):
                raise ValueError('unsafe closure filename')
            if (type(expected) is not dict or set(expected) != {'bytes', 'sha256'}
                    or type(expected['bytes']) is not int or not 0 <= expected['bytes'] <= 32 * 1024**2
                    or type(expected['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', expected['sha256'])):
                raise ValueError('invalid file pin')
            if regular(root / name).st_size != expected['bytes'] or pin(root / name) != expected:
                raise ValueError('copied file bytes/hash mismatch: ' + name)
            total += expected['bytes']
        if total > 1024**3:
            raise ValueError('model output exceeds recorded budget')
        status, kind = closure['status'], 'model-output'
    return {'root': str(root), 'kind': kind, 'integrity': 'passed',
            'recorded_status': status, 'closure_pin': closure_pin,
            'external_source_closure_checked': expected_closure_sha256 is not None,
            'evaluation_replayed': False, 'formal_permission': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--expected-closure-sha256')
    args = parser.parse_args(argv)
    try:
        report = verify(args.root, args.expected_closure_sha256)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'integrity': 'failed', 'type': type(error).__name__,
                          'message': str(error), 'formal_permission': False}))
        return 1
    print(json.dumps(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
