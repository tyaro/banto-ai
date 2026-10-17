"""Measure seven selected-source Git calls without claiming five-role closure.

The externally pinned Git policy and clean revision are inputs. The result
only binds one owner source check; the Job and its remaining Git calls are not
run by this tool.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import anomaly_v03 as v  # noqa: E402
from banto_ai import anomaly_v03_consumer_evidence as evidence  # noqa: E402
from banto_ai import anomaly_v03_preformal_five_role_job_owner as owner  # noqa: E402
from banto_ai import anomaly_v03_preformal_owned_source_git_session as source_git  # noqa: E402
from banto_ai import anomaly_v03_reader_evidence as observed  # noqa: E402
from banto_ai import _anomaly_v03_io as io  # noqa: E402


FORMAT = 'anomaly-v03-preformal-owned-source-git-trial-v1'
PHASE = 'owner-source-read'
OUTPUT_NAME = re.compile(
    r'anomaly-v03-preformal-owned-source-git-[a-z0-9][a-z0-9-]*\Z')
MAX_RESULT = 32 * 1024


def _pin_arg(value):
    matched = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if matched is None:
        raise argparse.ArgumentTypeError('expected bytes:sha256')
    return {'bytes': int(matched.group(1)), 'sha256': matched.group(2)}


def _root(value):
    path = Path(value)
    v.require(path.is_absolute() and path.parent == ROOT / 'artifacts' and
              OUTPUT_NAME.fullmatch(path.name) is not None,
              'known local source Git trial root')
    return path


def _calls(manifest, source):
    v.require(type(source) is dict and set(source) ==
              {'revision', 'orchestrator_selected', 'owner', 'scope'} and
              source['scope'] ==
              'clean-head-selected-working-raw-not-source-closure' and
              type(source['orchestrator_selected']) is dict and
              set(source['orchestrator_selected']) == set(owner.chain.SOURCES),
              'selected owner source scope')
    expected = [('head', 'head', None, None),
                ('status', 'status', None, None)]
    for index, name in enumerate(owner.chain.SOURCES):
        expected.append((f'selected-source-{index}', 'source_blob', name,
                         source['orchestrator_selected'][name]))
    expected.append(('owner-source', 'source_blob', owner.SOURCE,
                     source['owner']))
    v.require(type(manifest['calls']) is list and
              len(manifest['calls']) == len(expected) == 7,
              'exact seven selected source Git calls')
    for row, (call_id, operation, path, pin) in zip(manifest['calls'], expected):
        if pin is not None:
            evidence._pin(pin)
        v.require(row['call_id'] == call_id and
                  row['operation'] == operation and
                  row['source_path'] == path and
                  row['expected_output_pin'] == pin and
                  row['call_status'] == 'verified' and
                  row['receipt_pin'] is not None and
                  row['error_type'] is None,
                  'ordered owned selected source Git receipt ' + call_id)
        evidence._pin(row['receipt_pin'])


def verify_saved(result_root, expected_result_pin):
    target = _root(result_root)
    evidence._pin(expected_result_pin)
    raw = observed._file(target / 'result.json', MAX_RESULT)
    evidence._raw(raw, expected_result_pin, 'saved source Git trial result')
    result = v.strict_json(raw)
    v.require(raw == io.json_bytes(result) and
              type(result) is dict and set(result) == {
                  'format', 'status', 'scope', 'root', 'revision',
                  'policy_path', 'policy_pin', 'session_manifest_pin',
                  'source', 'call_count', 'integration_pending',
                  'registered_data_read', 'formal_permission',
                  'source_closure_complete', 'runtime_closure_complete',
                  'execution_authenticated'} and
              result['format'] == FORMAT and result['status'] == 'verified' and
              result['scope'] == 'seven-direct-selected-source-Git-calls-only' and
              result['root'] == str(target) and
              result['integration_pending'] is True and
              result['call_count'] == 7 and
              all(result[key] is False for key in (
                  'registered_data_read', 'formal_permission',
                  'source_closure_complete', 'runtime_closure_complete',
                  'execution_authenticated')),
              'retained selected source Git trial scope')
    evidence._digest(result['revision'], 40)
    evidence._pin(result['policy_pin'])
    evidence._pin(result['session_manifest_pin'])
    v.require(result['source']['revision'] == result['revision'],
              'selected source revision binding')
    saved = source_git.verify_retained(
        target / 'git', result['session_manifest_pin'],
        policy_path=result['policy_path'],
        expected_policy_pin=result['policy_pin'],
        revision=result['revision'], phase=PHASE)
    v.require(saved['call_status'] == 'verified' and
              saved['call_count'] == 7 and
              saved['formal_permission'] is False and
              saved['integration_pending'] is True,
              'retained seven-call owned session')
    _calls({'calls': saved['calls']}, result['source'])
    return {'status': 'verified_retained',
            'result_pin': expected_result_pin, 'call_count': 7,
            'formal_permission': False, 'integration_pending': True}


def run(*, policy_path, expected_policy_pin, revision, output_root):
    evidence._digest(revision, 40)
    target = _root(output_root)
    io.regular_path(target, directory=True, missing=True)
    v.require(not target.exists(), 'new source Git trial root required')
    # Reject an unpinned/mismatched policy before reserving the attempt root.
    source_git._policy(policy_path, expected_policy_pin, revision,
                       target / 'git')
    target.mkdir()  # No overwrite; an aborted attempt keeps its own root.
    with source_git.OwnedSourceGitSession(
            policy_path=policy_path, expected_policy_pin=expected_policy_pin,
            revision=revision, receipt_root=target / 'git', phase=PHASE) as session:
        source = owner._source(revision, git_reader=session)
    saved = session.manifest_result
    v.require(saved['status'] == 'verified' and saved['call_count'] == 7,
              'seven owned selected source Git calls')
    checked = source_git.verify_retained(
        target / 'git', saved['manifest_pin'], policy_path=policy_path,
        expected_policy_pin=expected_policy_pin,
        revision=revision, phase=PHASE)
    v.require(checked['call_status'] == 'verified' and
              checked['call_count'] == 7,
              'verified owned selected source manifest')
    _calls({'calls': checked['calls']}, source)
    result = {'format': FORMAT, 'status': 'verified',
              'scope': 'seven-direct-selected-source-Git-calls-only',
              'root': str(target), 'revision': revision,
              'policy_path': str(policy_path),
              'policy_pin': expected_policy_pin,
              'session_manifest_pin': saved['manifest_pin'],
              'source': source, 'call_count': 7,
              'integration_pending': True, 'registered_data_read': False,
              'formal_permission': False, 'source_closure_complete': False,
              'runtime_closure_complete': False,
              'execution_authenticated': False}
    raw = io.json_bytes(result)
    v.require(len(raw) <= MAX_RESULT, 'selected source Git result bound')
    io._exclusive(target / 'result.json', raw)
    pin = observed._pin(raw)
    verify_saved(target, pin)
    return {'status': 'verified', 'root': str(target), 'result_pin': pin,
            'manifest_pin': saved['manifest_pin'], 'call_count': 7,
            'formal_permission': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    active = commands.add_parser('run')
    active.add_argument('--policy-path', type=Path, required=True)
    active.add_argument('--policy-pin', type=_pin_arg, required=True)
    active.add_argument('--revision', required=True)
    active.add_argument('--output-root', type=Path, required=True)
    verify = commands.add_parser('verify')
    verify.add_argument('--result-root', type=Path, required=True)
    verify.add_argument('--result-pin', type=_pin_arg, required=True)
    args = parser.parse_args(argv)
    output = (run(policy_path=args.policy_path,
                  expected_policy_pin=args.policy_pin,
                  revision=args.revision, output_root=args.output_root)
              if args.command == 'run' else
              verify_saved(args.result_root, args.result_pin))
    print(json.dumps(output, sort_keys=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
