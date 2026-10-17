"""Bind owned publication role Git to retained role observations."""
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_platform_fixture as platform
from . import anomaly_v03_preformal_analysis_git as shared
from . import anomaly_v03_preformal_owned_source_git_session as source_git

publication, observed = platform.publication, shared.observed


def expected_calls(owner_root, saved_owner, policy, *, role='writer'):
    v.require(role in ('writer', 'reader'), 'owned publication Git binding role')
    def _pinned(path, pin, maximum):
        return shared._pinned(path, pin, maximum, role=role)
    root = Path(owner_root) / 'five-role'
    revision = saved_owner['source_revision']
    top = _pinned(root/'result.json', saved_owner['inner_result_pin'], 64*1024)
    v.require(top['status'] == 'verified' and top['source_revision'] == revision,
              role + ' Git top binding')
    pub_root = root/'publication'
    pub = _pinned(pub_root/'result.json', top['publication']['result_pin'], 64*1024)
    v.require(pub['format'] == 'anomaly-v03-fixture-publication-check-v1' and
              pub['status'] == 'verified' and pub['mode'] == 'fixture' and
              pub['publication_status'] == pub['reader_status'] == 'completed' and
              pub['profile_required'] is False and pub['formal_permission'] is False and
              pub['source_closure_complete'] is False and pub['runtime_closure_complete'] is False,
              role + ' Git publication scope')
    target = pub_root/role
    result_pin = observed._pin(publication.io.json_bytes(pub[role]))
    result = _pinned(target/'result.json', result_pin, 64*1024)
    v.require(result == pub[role] and result['status'] == 'verified' and
              result['role'] == role and result['worker_exit_confirmed'] is True and
              result['source_revision'] == revision and result['profile_required'] is False,
              role + ' Git role scope')
    invocation = _pinned(target/'invocation.json', result['invocation_pin'], 64*1024)
    source = invocation['source']
    evidence._source(source)
    v.require(invocation['format'] == publication.INVOCATION and invocation['role'] == role
              and source['revision'] == revision and
              [row['path'] for row in source['sources']] == list(platform.SOURCE_FILES) and
              pub['selected_source_files'] == len(platform.SOURCE_FILES),
              role + ' Git selected source binding')
    selected = {row['path']: {'bytes': row['byte_count'], 'sha256': row['raw_sha256']}
                for row in source['sources']}
    reply = _pinned(target/'worker/report.json', result['stdout_pin'], publication.LIMITS['output_bytes'])
    record = _pinned(target/'evidence.json', result['evidence_pin'], 64*1024)
    v.require(reply['evidence'] == record and record['role'] == role and
              record['mode'] == 'fixture' and record['invocation_id'] == invocation['invocation_id']
              and record['source_before'] == source and record['source_after'] == source,
              role + ' Git child source binding')
    pair = _pinned(target/'dependencies.json', result['dependency_pin'], publication.LIMITS['output_bytes'])
    v.require(pair == {'before': reply['dependencies_before'], 'after': reply['dependencies_after']},
              role + ' Git child dependency binding')
    tool = _pinned(target/'source-tool.json', result['source_tool_pin'], 16*1024)
    v.require(tool == {'path': policy['executable_path'], 'pin': policy['executable_pin'],
                      'hardlinks': policy['executable_links'], 'full_tool_runtime_closure': False},
              role + ' Git tool/policy binding')
    dependencies, before_rows = {}, None
    for phase in ('before', 'after'):
        rows = pair[phase]['files']
        v.require(type(rows) is dict and 0 < len(rows) <= publication.dependencies.MAX_FILES,
                  role + ' Git dependency inventory bound')
        if before_rows is not None:
            v.require(all(name in rows and rows[name] == row for name, row in before_rows.items()),
                      role + ' Git dependency changed between phases')
        for logical, row in rows.items():
            if row['category'] != 'project':
                if logical.startswith('project/'):
                    name = logical[len('project/'):]
                    v.safe_relative_path(name)
                    v.require(row['category'] == 'bytecode-cache-candidate' and row['native'] is False
                              and Path(name).suffix == '.pyc' and
                              Path(row['physical_path']) == publication.ROOT/name,
                              role + ' Git project cache category')
                continue
            v.require(logical.startswith('project/'), role + ' Git logical source path')
            name = logical[len('project/'):]
            v.safe_relative_path(name)
            v.require(name.startswith('src/') and row['native'] is False and
                      Path(row['physical_path']) == publication.ROOT/name,
                      role + ' Git physical source path')
            evidence._pin(row['pin'])
            v.require(name not in dependencies or dependencies[name] == row['pin'],
                      role + ' Git dependency pin changed')
            dependencies[name] = row['pin']
        v.require(set(selected) <= set(dependencies), role + ' Git required dependencies')
        before_rows = rows
    v.require(len(dependencies) <= 64 and
              result['dependency_observation']['project_files'] == len(dependencies) and
              all(dependencies[name] == pin for name, pin in selected.items()),
              role + ' Git selected/dependency binding')
    expected = [('head', None, None)]
    expected.extend(('source_blob', name, selected[name]) for name in publication.observed.SOURCE_FILES)
    expected.append(('status', None, None))
    expected.extend(('source_blob', name, selected[name]) for name in platform.EXTRA_SOURCES)
    expected.extend([('head', None, None), ('status', None, None)])
    expected.extend([('head', None, None)]*3)
    expected.extend(('source_blob', name, pin) for name, pin in dependencies.items() if name not in selected)
    return [(f'{role}-git-{i}', operation, name, pin)
            for i, (operation, name, pin) in enumerate(expected)]


def verify_manifest(target, receipt, saved_owner, *, phase, role='writer'):
    v.require(role in ('writer', 'reader'), 'owned publication Git manifest role')
    checked = source_git.verify_retained(
        Path(target)/'attempt'/f'{role}-git', receipt[role + '_git_manifest_pin'],
        policy_path=receipt['git_policy_path'], expected_policy_pin=receipt['git_policy_pin'],
        revision=receipt['source_revision'], phase=phase)
    v.require(checked['call_status'] == receipt[role + '_git_status'] and
              checked['call_count'] == receipt[role + '_git_call_count'] and
              checked['formal_permission'] is False and checked['source_closure_complete'] is False
              and checked['runtime_closure_complete'] is False, role + ' Git retained scope')
    if saved_owner['status'] == 'verified':
        v.require(checked['call_status'] == 'verified', role + ' Git manifest required')
        policy = v.strict_json(observed._file(receipt['git_policy_path'], source_git.MAX_POLICY))
        from .anomaly_v03_preformal_producer_git_binding import verify_calls
        verify_calls(checked['calls'], expected_calls(Path(target)/'attempt', saved_owner, policy, role=role),
                     label=role)
    return checked
