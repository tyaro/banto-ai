"""Prepare and run one invented, owned, registered-format generation trial.

The ``prepare`` phase derives pins in the caller process and retains them in
an external manifest before the owned generator is launched.  The ``run``
phase consumes only that caller-pinned manifest.  Neither phase uses a
registered holdout seed or actual registered observation bytes, and neither
grants formal credit.

Example (after committing a clean source revision)::

    python -B tools/preformal_owned_generated_trial.py prepare \
      --root artifacts/anomaly-v03-preformal-registered-attempt-g01 \
      --manifest artifacts/anomaly-v03-preformal-generated-pinsets-g01/pins.json
    python -B tools/preformal_owned_generated_trial.py run \
      --root artifacts/anomaly-v03-preformal-registered-attempt-g01 \
      --manifest artifacts/anomaly-v03-preformal-generated-pinsets-g01/pins.json \
      --manifest-sha256 <sha256 printed by prepare>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import _anomaly_v03_io as io  # noqa: E402
from banto_ai import _anomaly_v03_runtime as paths  # noqa: E402
from banto_ai import anomaly_v03 as v  # noqa: E402
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated  # noqa: E402
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as copied  # noqa: E402
from banto_ai import anomaly_v03_reader_evidence as observed  # noqa: E402


FORMAT = 'anomaly-v03-preformal-owned-generated-external-pins-v1'
MAX_MANIFEST = 256 * 1024
MAX_RESULT = 256 * 1024
MANIFEST_FIELDS = {
    'format', 'scope', 'root', 'revision', 'chunk_index', 'recipe_id',
    'source', 'source_snapshots', 'source_snapshot_pins', 'output_pins',
    'output_file_count', 'output_bytes', 'invented_only',
    'actual_registered_observations_read', 'formal_permission',
}


def _argument_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _manifest_path(value: str, root: Path, *, missing: bool) -> Path:
    path = paths.regular_path(_argument_path(value), missing=missing)
    parent = paths.regular_path(path.parent, directory=True, missing=missing)
    v.require(parent.parent == ROOT / 'artifacts' and
              parent.name.startswith('anomaly-v03-preformal-generated-pinsets-')
              and parent != root,
              'separate dedicated external pinset directory required')
    v.require(path.name.endswith('.json'), 'JSON external manifest required')
    return path


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + '.sha256')


def _revision() -> str:
    revision = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        stderr=subprocess.DEVNULL, timeout=10).decode('ascii').strip()
    v.require(bool(re.fullmatch(r'[0-9a-f]{40}', revision)), 'full clean HEAD required')
    return revision


def _snapshots(revision: str) -> dict[str, dict[str, bytes]]:
    rows = {}
    for name in generated.SNAPSHOT_FILES:
        working = observed._file(ROOT / name, 1024**2)
        committed = subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', revision + ':' + name],
            stderr=subprocess.DEVNULL, timeout=10)
        v.require(working == committed, 'snapshot working/Git mismatch: ' + name)
        rows[name] = working
    snapshots = {revision: rows}
    generated._validated_snapshots(snapshots, revision)
    return snapshots


def _snapshot_pins(snapshots: dict[str, dict[str, bytes]], revision: str) -> dict:
    return {name: copied._pin(raw)
            for name, raw in sorted(snapshots[revision].items())}


def prepare(root_text: str, manifest_text: str, chunk_index: int) -> int:
    root = generated._root(_argument_path(root_text), missing=True)
    v.require(not root.exists(), 'prepare requires a new generated-attempt root')
    names = generated._outputs(root, chunk_index)
    manifest_path = _manifest_path(manifest_text, root, missing=True)
    sidecar = _sidecar(manifest_path)
    paths.regular_path(sidecar, missing=True)
    v.require(not manifest_path.exists() and not sidecar.exists(),
              'external manifest and SHA sidecar must be new')

    revision = _revision()
    source = generated._source(revision)
    snapshots = _snapshots(revision)
    output = generated.build_invented_output_bytes(
        root, chunk_index=chunk_index, recipe_id=generated.RECIPE,
        source_snapshots=snapshots)
    v.require(set(output) == set(names), 'exact invented output inventory')
    pins = {name: copied._pin(raw) for name, raw in sorted(output.items())}
    generated._validate_pins(names, pins)
    manifest = {
        'format': FORMAT,
        'scope': 'invented-registered-format-owned-generator-only',
        'root': str(root), 'revision': revision,
        'chunk_index': chunk_index, 'recipe_id': generated.RECIPE,
        'source': source,
        'source_snapshots': copied._source_snapshots(snapshots),
        'source_snapshot_pins': _snapshot_pins(snapshots, revision),
        'output_pins': pins, 'output_file_count': len(pins),
        'output_bytes': sum(pin['bytes'] for pin in pins.values()),
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    }
    raw = v.canonical_json(manifest)
    v.require(len(raw) <= MAX_MANIFEST, 'external manifest byte bound')
    digest = hashlib.sha256(raw).hexdigest()
    manifest_path.parent.mkdir(exist_ok=True)
    io._exclusive(manifest_path, raw)
    io._exclusive(sidecar, (digest + '\n').encode('ascii'))
    print(json.dumps({
        'status': 'prepared', 'manifest': str(manifest_path),
        'manifest_sha256': digest, 'sha256_sidecar': str(sidecar),
        'root': str(root), 'revision': revision,
        'output_file_count': len(pins), 'output_bytes': manifest['output_bytes'],
        'invented_only': True, 'formal_permission': False,
    }, sort_keys=True))
    return 0


def run(root_text: str, manifest_text: str, digest: str) -> int:
    v.require(bool(re.fullmatch(r'[0-9a-f]{64}', digest)),
              'caller-supplied manifest SHA-256 required')
    root = generated._root(_argument_path(root_text), missing=True)
    manifest_path = _manifest_path(manifest_text, root, missing=False)
    raw = observed._file(manifest_path, MAX_MANIFEST)
    v.require(hashlib.sha256(raw).hexdigest() == digest,
              'caller-supplied external manifest SHA mismatch')
    sidecar = _sidecar(manifest_path)
    v.require(observed._file(sidecar, 128) == (digest + '\n').encode('ascii'),
              'external manifest SHA sidecar mismatch')
    manifest = v.strict_json(raw)
    v.require(raw == v.canonical_json(manifest) and
              type(manifest) is dict and set(manifest) == MANIFEST_FIELDS,
              'canonical exact external manifest required')
    v.require(manifest['format'] == FORMAT and
              manifest['scope'] == 'invented-registered-format-owned-generator-only'
              and manifest['root'] == str(root) and
              manifest['recipe_id'] == generated.RECIPE and
              manifest['invented_only'] is True and
              manifest['actual_registered_observations_read'] is False and
              manifest['formal_permission'] is False,
              'invented external manifest identity/scope mismatch')
    revision = _revision()
    v.require(manifest['revision'] == revision,
              'external manifest full HEAD mismatch')
    source = generated._source(revision)
    v.require(manifest['source'] == source,
              'external manifest selected source mismatch')
    snapshots = copied._decode_source_snapshots(manifest['source_snapshots'])
    generated._validated_snapshots(snapshots, revision)
    v.require(manifest['source_snapshot_pins'] ==
              _snapshot_pins(snapshots, revision),
              'external generator/materializer raw snapshot pins changed')
    names = generated._outputs(root, manifest['chunk_index'])
    pins = manifest['output_pins']
    generated._validate_pins(names, pins)
    v.require(manifest['output_file_count'] == len(names) == 22 and
              manifest['output_bytes'] ==
              sum(pin['bytes'] for pin in pins.values()),
              'external output inventory size mismatch')

    if root.exists():
        paths.regular_path(root, directory=True)
        v.require(not any(root.iterdir()), 'generated-attempt root must be empty')
    else:
        root.mkdir()
    result = generated.generate_and_read(
        root, expected_pins=pins, source_snapshots=snapshots,
        expected_revision=revision, chunk_index=manifest['chunk_index'],
        recipe_id=generated.RECIPE)
    saved_result = observed._file(root / 'owned-generator' / 'result.json',
                                  MAX_RESULT)
    v.require(copied._pin(saved_result) == result['result_pin'] and
              v.strict_json(saved_result) == {
                  key: value for key, value in result.items()
                  if key not in ('result_pin', 'check_directory')},
              'owned generator result retention/readback')
    print(v.canonical_json(result).decode('utf-8'))
    return 0 if result['status'] == 'verified' else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    phases = parser.add_subparsers(dest='phase', required=True)
    before = phases.add_parser('prepare', help='save external invented output pins')
    before.add_argument('--root', required=True)
    before.add_argument('--manifest', required=True)
    before.add_argument('--chunk-index', type=int, default=0)
    after = phases.add_parser('run', help='consume a caller-pinned external manifest')
    after.add_argument('--root', required=True)
    after.add_argument('--manifest', required=True)
    after.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    try:
        if args.phase == 'prepare':
            return prepare(args.root, args.manifest, args.chunk_index)
        return run(args.root, args.manifest, args.manifest_sha256)
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'rejected', 'phase': args.phase,
                          'error_type': type(error).__name__,
                          'detail': str(error), 'formal_permission': False},
                         sort_keys=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
