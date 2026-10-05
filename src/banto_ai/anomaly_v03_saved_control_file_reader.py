"""Bounded pinned disk reads of an invented 480-chunk control fixture.

These files are retained reader declarations/rows, not observation payloads.
The caller owns the external index pin. Paths are derived from chunk position
and the ten fixed names; descriptors cannot redirect a read. No process or
registered campaign origin is authenticated here.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_observation_audit as pinned
from . import anomaly_v03_preformal_saved_row_coverage as coverage
from . import anomaly_v03_saved_row_document_publication as publication


ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'anomaly-v03-saved-row-projection-'
FORMAT = 'anomaly-v03-saved-control-file-reader-v1'
PIPELINE_FORMAT = 'anomaly-v03-saved-control-files-document-publication-v1'
SCOPE = 'pinned-invented-control-disk-reads-to-50000-document-local-fresh-reader'
INDEX_FORMAT = 'anomaly-v03-invented-saved-row-controls-v1'
CHUNKS = 480
MAX_INDEX_BYTES = 1024**2
MAX_INPUT_BYTES = coverage.MAX_TOTAL_INPUT_BYTES
SOURCE_NAMES = (
    'src/banto_ai/anomaly_v03_saved_control_file_reader.py',
    'src/banto_ai/anomaly_v03_observation_audit.py',
)


class ControlFileBudget(publication.PublicationBudget):
    phase_names = ('preflight', 'control-read', 'analysis', 'audit', 'document',
                   'slices', 'writer', 'reader', 'control-reread', 'postflight')

    def close(self):
        report = super().close()
        report.update(format=PIPELINE_FORMAT + '-resource-budget', scope=SCOPE,
                      saved_control_loading_inside_budget=True,
                      saved_control_disk_reread_inside_budget=True,
                      external_saved_control_bytes_in_directory_budget=False,
                      external_saved_control_input_byte_limit=MAX_INPUT_BYTES,
                      real_saved_chunk_reader_used=False)
        return report


def validate_request(root, expected_pinset_pin):
    """Only lexical selection and pin shape; disk reads occur after start()."""
    evidence._pin(expected_pinset_pin)
    v.require(0 < expected_pinset_pin['bytes'] <= MAX_INDEX_BYTES,
              'control index external byte bound')
    root = Path(root).absolute()
    v.require(root.parent == ROOT / 'artifacts' and root.name.startswith(PREFIX)
              and root.name != PREFIX, 'dedicated invented control fixture root')
    return root


def _inventory(root, expected):
    paths.regular_path(root, directory=True)
    v.require({path.name for path in root.iterdir()} == set(expected),
              'control file inventory differs')


def _index(root, expected_pinset_pin, budget, phase):
    budget.checkpoint(phase)
    paths.regular_path(root, directory=True)
    raw = pinned.read_pinned(root / 'pinset.json', expected_pinset_pin, MAX_INDEX_BYTES)
    value = v.strict_json(raw)
    v.require(type(value) is dict and set(value) == {
        'format', 'entries', 'fixture_controls', 'formal_permission',
        'registered_observations_read', 'construction_used_cached_identity_fixture',
        'source_revision'} and raw == v.canonical_json(value),
        'exact canonical control index')
    v.require(value['format'] == INDEX_FORMAT and value['fixture_controls'] is True
              and value['formal_permission'] is False
              and value['registered_observations_read'] is False
              and type(value['construction_used_cached_identity_fixture']) is bool,
              'only invented control index is open')
    evidence._digest(value['source_revision'], 40)
    v.require(type(value['entries']) is list and len(value['entries']) == CHUNKS,
              'complete control index inventory')
    total = len(raw)
    for index, entry in enumerate(value['entries']):
        v.require(type(entry) is dict and set(entry) == set(coverage.RAW_LIMITS),
                  'exact control chunk names')
        for name, maximum in coverage.RAW_LIMITS.items():
            descriptor = entry[name]
            v.require(type(descriptor) is dict and set(descriptor) == {'path', 'pin'}
                      and descriptor['path'] == f'controls/{index:03d}/{name}.json',
                      'fixed control descriptor path')
            evidence._pin(descriptor['pin'])
            v.require(0 < descriptor['pin']['bytes'] <= maximum,
                      'control descriptor byte bound')
            total += descriptor['pin']['bytes']
            v.require(total <= MAX_INPUT_BYTES, 'control total input byte bound')
    _inventory(root / 'controls', [f'{index:03d}' for index in range(CHUNKS)])
    budget.checkpoint(phase)
    return raw, value, total


def _read_chunks(root, index, budget, phase, *, retain):
    entries = []
    for number, descriptors in enumerate(index['entries']):
        budget.checkpoint(phase)
        chunk = root / 'controls' / f'{number:03d}'
        _inventory(chunk, [name + '.json' for name in coverage.RAW_LIMITS])
        entry = {'expected_pins': {name: copy.deepcopy(value['pin'])
                                  for name, value in descriptors.items()}}
        for name, maximum in coverage.RAW_LIMITS.items():
            # Never follow descriptor['path']; it was checked against this name.
            raw = pinned.read_pinned(chunk / (name + '.json'), descriptors[name]['pin'], maximum)
            if retain:
                entry[name + '_raw'] = raw
        _inventory(chunk, [name + '.json' for name in coverage.RAW_LIMITS])
        if retain:
            entries.append(entry)
    budget.checkpoint(phase)
    return entries


def load_controls(root, *, expected_pinset_pin, budget):
    root = validate_request(root, expected_pinset_pin)
    raw, index, total = _index(root, expected_pinset_pin, budget, 'control-read')
    entries = _read_chunks(root, index, budget, 'control-read', retain=True)
    # The index remains anchored to the original externally retained pin.
    v.require(pinned.read_pinned(root / 'pinset.json', expected_pinset_pin, MAX_INDEX_BYTES) == raw,
              'control index changed during load')
    summary = {'format': FORMAT, 'scope': 'invented-control-files-only',
        'source_root': str(root), 'external_pinset_pin': copy.deepcopy(expected_pinset_pin),
        'fixture_construction_source_revision': index['source_revision'],
        'control_chunks': CHUNKS, 'control_files': CHUNKS * len(coverage.RAW_LIMITS),
        'control_bytes': total - len(raw), 'total_input_bytes_including_index': total,
        'input_byte_limit': MAX_INPUT_BYTES, 'disk_load_completed': True,
        'saved_control_loading_inside_budget': True,
        'external_saved_control_bytes_in_directory_budget': False,
        'real_saved_chunk_reader_used': False, 'producer_executed_here': False,
        'registered_observations_read': False, 'actual_registered_observations_read': False,
        'execution_authenticated': False, 'formal_permission': False,
        'campaign_evaluations_credited': 0, 'full_end_to_end_budget_measured': False}
    return {'entries': entries, 'summary': summary, 'index_raw': raw, 'index': index}


def recheck_controls(loaded, *, budget):
    summary = loaded['summary']
    root = validate_request(summary['source_root'], summary['external_pinset_pin'])
    raw, index, total = _index(root, summary['external_pinset_pin'], budget, 'control-reread')
    v.require(raw == loaded['index_raw'] and index == loaded['index'] and
              total == summary['total_input_bytes_including_index'],
              'control index changed before final reread')
    _read_chunks(root, index, budget, 'control-reread', retain=False)
    v.require(pinned.read_pinned(root / 'pinset.json', summary['external_pinset_pin'], MAX_INDEX_BYTES) == raw,
              'control index changed during final reread')
    return {'control_files': summary['control_files'], 'control_bytes': summary['control_bytes'],
            'disk_pin_recheck_completed': True, 'raw_observations_rederived': False,
            'formal_permission': False}
