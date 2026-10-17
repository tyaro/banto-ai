"""Single-read pinned input/transform loaders over immutable v1 contracts."""
from demand_input_boundary import *


def _pinned_json(path, expected_pin):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size>32*1024**2:raise ValueError('plain bounded file required')
    with path.open('rb') as stream:
        raw=stream.read(32*1024**2+1)
    if len(raw)>32*1024**2 or pin_bytes(raw)!=expected_pin:raise ValueError('exact decoded-bytes pin mismatch')
    return strict_json(raw)


def load_inputs(path, expected_pin):
    rows=_pinned_json(path,expected_pin)
    if type(rows) is not list:raise ValueError('input list required')
    seen=set()
    for row in rows:
        validate_input(row)
        if row['key'] in seen:raise ValueError('duplicate input key')
        seen.add(row['key'])
    return rows


def load_transforms(path, expected_pin):return validate_transforms(_pinned_json(path,expected_pin))
