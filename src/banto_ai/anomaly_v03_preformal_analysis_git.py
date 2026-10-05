"""Owned direct Git for fixture analysis and its saved inventory binding.

The observed dependency cache holds immutable revision blobs only. Loaded
code, Git descendants and full source/runtime closure remain unauthenticated.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_platform_numeric_fixture as numeric
from . import anomaly_v03_preformal_owned_source_git_session as source_git
from . import anomaly_v03_reader_evidence as observed


class OwnedAnalysisGit:
    def __init__(self, reader, *, root, revision):
        evidence._digest(revision, 40)
        v.require(reader.revision == revision, 'analysis owned Git revision')
        self.reader, self.root, self.revision = reader, Path(root), revision
        policy = reader.policy
        self.tool_record = {'path': policy['executable_path'],
                            'pin': copy.deepcopy(policy['executable_pin']),
                            'hardlinks': policy['executable_links'],
                            'full_tool_runtime_closure': False}
        self.index = 0
        self.cache = None

    def start_dependencies(self):
        v.require(self.cache is None, 'analysis dependency cache starts once')
        self.cache = {}

    def __call__(self, *args):
        name = pin = None
        if args == ('rev-parse', 'HEAD'):
            operation = 'head'
        elif args == ('status', '--porcelain'):
            operation = 'status'
        else:
            v.require(len(args) == 2 and args[0] == 'show' and
                      type(args[1]) is str and args[1].startswith(self.revision + ':'),
                      'analysis owned Git request')
            name = args[1][len(self.revision) + 1:]
            v.safe_relative_path(name)
            v.require(name.startswith('src/'), 'analysis owned Git source path')
            if self.cache is not None and name in self.cache:
                return self.cache[name]
            pin = observed._pin(observed._file(self.root / name, 1024**2))
            operation = 'source_blob'
        raw = self.reader.run(call_id=f'analysis-git-{self.index}', operation=operation,
                              source_path=name, expected_output_pin=pin)
        self.index += 1
        if operation == 'source_blob' and self.cache is not None:
            self.cache[name] = raw
        return raw


def _pinned(path, pin, maximum):
    evidence._pin(pin)
    raw = observed._file(path, maximum)
    evidence._raw(raw, pin, 'analysis Git binding ' + str(path))
    return v.strict_json(raw)


def expected_calls(owner_root, saved_owner, policy):
    root = Path(owner_root) / 'five-role'
    revision = saved_owner['source_revision']
    top = _pinned(root / 'result.json', saved_owner['inner_result_pin'], 64 * 1024)
    v.require(top['status'] == 'verified' and top['source_revision'] == revision,
              'analysis Git top binding')
    target = root / 'analysis'
    result = _pinned(target / 'result.json', top['analysis']['result_pin'], 64 * 1024)
    v.require(result['format'] == 'anomaly-v03-fixture-worker-check-v1' and
              result['status'] == 'verified' and result['mode'] == 'fixture' and
              result['role'] == 'analysis' and result['profile_required'] is False and
              result['formal_permission'] is False and
              result['source_closure_complete'] is False and
              result['runtime_closure_complete'] is False,
              'analysis Git role scope')
    invocation = _pinned(target / 'invocation.json', result['invocation_pin'], 64 * 1024)
    source = invocation['source']
    evidence._source(source)
    v.require(invocation['format'] == numeric.analysis.INVOCATION and
              source['revision'] == revision and
              [row['path'] for row in source['sources']] == list(numeric.SOURCE_FILES),
              'analysis Git selected source binding')
    selected = {row['path']: {'bytes': row['byte_count'], 'sha256': row['raw_sha256']}
                for row in source['sources']}
    reply = _pinned(target / 'worker' / 'report.json', result['stdout_pin'],
                    numeric.analysis.LIMITS['output_bytes'])
    record = _pinned(target / 'evidence.json', result['evidence_pin'], 64 * 1024)
    v.require(reply['evidence'] == record and record['role'] == 'analysis' and
              record['mode'] == 'fixture' and record['invocation_id'] == invocation['invocation_id']
              and record['source_before'] == source and record['source_after'] == source,
              'analysis Git child source binding')
    pair = _pinned(target / 'dependencies.json', result['dependency_pin'],
                   numeric.analysis.LIMITS['output_bytes'])
    v.require(pair == {'before': reply['dependencies_before'], 'after': reply['dependencies_after']},
              'analysis Git child dependency binding')
    tool = _pinned(target / 'source-tool.json', result['source_tool_pin'], 16 * 1024)
    v.require(tool == {'path': policy['executable_path'], 'pin': policy['executable_pin'],
                      'hardlinks': policy['executable_links'], 'full_tool_runtime_closure': False},
              'analysis Git tool/policy binding')
    dependencies = {}
    before_rows = None
    for phase in ('before', 'after'):
        rows = pair[phase]['files']
        v.require(type(rows) is dict and 0 < len(rows) <= numeric.analysis.dependencies.MAX_FILES,
                  'analysis Git dependency inventory bound')
        if before_rows is not None:
            v.require(all(name in rows and rows[name] == row for name, row in before_rows.items()),
                      'analysis Git dependency changed between phases')
        for logical, row in rows.items():
            if row['category'] != 'project':
                if logical.startswith('project/'):
                    name = logical[len('project/'):]
                    v.safe_relative_path(name)
                    v.require(row['category'] == 'bytecode-cache-candidate' and row['native'] is False
                              and Path(name).suffix == '.pyc' and
                              Path(row['physical_path']) == numeric.analysis.ROOT / name,
                              'analysis Git project cache category')
                continue
            v.require(logical.startswith('project/'), 'analysis Git logical source path')
            name = logical[len('project/'):]
            v.safe_relative_path(name)
            v.require(name.startswith('src/') and row['native'] is False and
                      Path(row['physical_path']) == numeric.analysis.ROOT / name,
                      'analysis Git physical source path')
            evidence._pin(row['pin'])
            v.require(name not in dependencies or dependencies[name] == row['pin'],
                      'analysis Git dependency pin changed')
            dependencies[name] = row['pin']
        v.require(set(selected) <= set(dependencies), 'analysis Git required dependencies')
        before_rows = rows
    v.require(result['dependency_observation']['project_files'] == len(dependencies) and
              all(dependencies[name] == pin for name, pin in selected.items()),
              'analysis Git selected/dependency binding')
    expected = [('head', None, None)]
    expected.extend(('source_blob', name, selected[name]) for name in numeric.analysis.observed.SOURCE_FILES)
    expected.append(('status', None, None))
    expected.extend(('source_blob', name, selected[name]) for name in numeric.EXTRA_SOURCES)
    expected.extend([('head', None, None)] * 2)
    expected.extend(('source_blob', name, pin) for name, pin in dependencies.items())
    return [(f'analysis-git-{i}', operation, name, pin)
            for i, (operation, name, pin) in enumerate(expected)]


def verify_manifest(target, receipt, saved_owner, *, phase):
    checked = source_git.verify_retained(
        Path(target) / 'attempt' / 'analysis-git', receipt['analysis_git_manifest_pin'],
        policy_path=receipt['git_policy_path'], expected_policy_pin=receipt['git_policy_pin'],
        revision=receipt['source_revision'], phase=phase)
    v.require(checked['call_status'] == receipt['analysis_git_status'] and
              checked['call_count'] == receipt['analysis_git_call_count'] and
              checked['formal_permission'] is False and checked['source_closure_complete'] is False
              and checked['runtime_closure_complete'] is False, 'analysis Git retained scope')
    if saved_owner['status'] == 'verified':
        v.require(checked['call_status'] == 'verified', 'analysis Git manifest required')
        policy = v.strict_json(observed._file(receipt['git_policy_path'], source_git.MAX_POLICY))
        from .anomaly_v03_preformal_producer_git_binding import verify_calls
        verify_calls(checked['calls'], expected_calls(Path(target) / 'attempt', saved_owner, policy),
                     label='analysis')
    return checked
