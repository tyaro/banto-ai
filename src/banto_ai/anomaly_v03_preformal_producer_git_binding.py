"""Bind saved producer Git calls to its pinned invocation and child inventory.

This covers direct source reads in the fixture producer parent. It does not
authenticate Git descendants, loaded code, or a complete dependency closure.
"""
from __future__ import annotations

from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_owned_producer_fixture as producer
from . import anomaly_v03_preformal_owned_source_git_session as source_git
from . import anomaly_v03_reader_evidence as observed


def _pinned(path, pin, maximum):
    evidence._pin(pin)
    raw = observed._file(path, maximum)
    evidence._raw(raw, pin, 'producer Git binding ' + str(path))
    return v.strict_json(raw)


def expected_calls(owner_root, saved_owner):
    """Derive an exact inventory from the saved, externally pinned role chain."""
    root = Path(owner_root) / 'five-role'
    top = _pinned(root / 'result.json', saved_owner['inner_result_pin'], 64 * 1024)
    revision = saved_owner['source_revision']
    v.require(top['status'] == 'verified' and top['source_revision'] == revision,
              'producer Git top result binding')
    target = root / 'producer'
    result = _pinned(target / 'result.json', top['producer']['result_pin'], 64 * 1024)
    v.require(result['format'] == producer.FORMAT and result['status'] == 'verified'
              and result['mode'] == 'fixture' and result['source_revision'] == revision
              and result['profile_required'] is False and
              result['source_closure_complete'] is False and
              result['runtime_closure_complete'] is False and
              result['formal_permission'] is False,
              'producer Git role scope')
    invocation = _pinned(target / 'invocation.json', result['invocation_pin'], 16 * 1024)
    source = invocation['source']
    evidence._keys(source, 'revision selected_files scope', 'producer selected source')
    v.require(invocation['format'] == producer.INVOCATION and
              invocation['source_revision'] == revision and
              source['revision'] == revision and
              source['scope'] == 'selected-working-raw-only-not-source-closure' and
              type(source['selected_files']) is list and
              len(source['selected_files']) == len(producer.SOURCE_FILES),
              'producer Git selected source binding')
    for row, name in zip(source['selected_files'], producer.SOURCE_FILES):
        evidence._keys(row, 'path pin', 'producer selected source row')
        v.require(row['path'] == name, 'producer Git selected source order')
        evidence._pin(row['pin'])
    reply = _pinned(target / 'worker' / 'report.json', result['stdout_pin'],
                    producer.LIMITS['output_bytes'])
    v.require(reply['format'] == producer.FORMAT and reply['status'] == 'joined' and
              reply['invocation_id'] == invocation['invocation_id'] and
              reply['source_before'] == source and reply['source_after'] == source,
              'producer Git child source binding')
    pair = _pinned(target / 'dependencies.json', result['dependency_pin'],
                   producer.LIMITS['output_bytes'])
    evidence._keys(pair, 'before after', 'producer dependency pair')
    v.require(pair == {'before': reply['dependencies_before'],
                       'after': reply['dependencies_after']},
              'producer Git child dependency pair binding')
    dependencies = {}
    before_rows = None
    for phase in ('before', 'after'):
        rows = pair[phase]['files']
        v.require(type(rows) is dict and 0 < len(rows) <= producer.dependencies.MAX_FILES,
                  'producer Git dependency inventory bound')
        if before_rows is not None:
            v.require(all(name in rows and rows[name] == row
                          for name, row in before_rows.items()),
                      'producer Git dependency changed between phases')
        for logical, row in rows.items():
            if row['category'] != 'project':
                if logical.startswith('project/'):
                    name = logical[len('project/'):]
                    v.safe_relative_path(name)
                    v.require(row['category'] == 'bytecode-cache-candidate' and
                              row['native'] is False and Path(name).suffix == '.pyc' and
                              Path(row['physical_path']) == producer.ROOT / name,
                              'producer Git project cache category')
                continue
            v.require(logical.startswith('project/'), 'producer Git logical path')
            name = logical[len('project/'):]
            v.safe_relative_path(name)
            v.require(name.startswith('src/') and row['native'] is False and
                      Path(row['physical_path']) == producer.ROOT / name,
                      'producer Git physical source path')
            evidence._pin(row['pin'])
            if name in dependencies:
                v.require(dependencies[name] == row['pin'],
                          'producer Git dependency pin changed')
            else:
                dependencies[name] = row['pin']
        v.require({'project/' + name for name in producer.SOURCE_FILES} <= set(rows),
                  'producer Git required dependencies')
        before_rows = rows
    v.require(result['dependency_observation']['project_files'] == len(dependencies),
              'producer Git dependency count binding')
    for row in source['selected_files']:
        v.require(dependencies[row['path']] == row['pin'],
                  'producer Git selected/dependency pin binding')

    def group(index):
        prefix = f'producer-source-{index}-'
        return [(prefix + 'head', 'head', None, None)] + [
            (prefix + f'selected-source-{i}', 'source_blob', row['path'], row['pin'])
            for i, row in enumerate(source['selected_files'])]

    expected = []
    for index in range(3):
        expected.extend(group(index))
    expected.extend((f'producer-dependency-{i}', 'source_blob', name, pin)
                    for i, (name, pin) in enumerate(dependencies.items()))
    expected.extend(group(3))
    return expected


def verify_calls(calls, expected, *, label='producer'):
    v.require(type(calls) is list and len(calls) == len(expected),
              'exact ' + label + ' Git call count')
    for index, (row, (call_id, operation, path, pin)) in enumerate(zip(calls, expected)):
        v.require(row['index'] == index and row['call_id'] == call_id and
                  row['operation'] == operation and row['source_path'] == path and
                  row['expected_output_pin'] == pin and
                  row['call_status'] == 'verified' and row['receipt_pin'] is not None
                  and row['reason'] is None and row['error_type'] is None,
                  label + ' Git call order and pinned inventory')


def verify_manifest(target, receipt, saved_owner, *, phase):
    checked = source_git.verify_retained(
        Path(target) / 'attempt' / 'producer-git', receipt['producer_git_manifest_pin'],
        policy_path=receipt['git_policy_path'], expected_policy_pin=receipt['git_policy_pin'],
        revision=receipt['source_revision'], phase=phase)
    v.require(checked['call_status'] == receipt['producer_git_status'] and
              checked['call_count'] == receipt['producer_git_call_count'] and
              checked['formal_permission'] is False and
              checked['source_closure_complete'] is False and
              checked['runtime_closure_complete'] is False,
              'producer Git retained manifest scope')
    if saved_owner['status'] == 'verified':
        v.require(checked['call_status'] == 'verified', 'producer Git manifest required')
        verify_calls(checked['calls'], expected_calls(Path(target) / 'attempt', saved_owner))
    return checked
