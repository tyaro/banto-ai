"""Four owned parent HEAD/clean checks in the existing outer fixture budget.

Source blob calls, worker Git, loaded Git code and full closure remain open.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03_preformal_owned_source_git_session as sessions

v, observed, owned, paths = sessions.v, sessions.observed, sessions.owned_git, sessions.paths
SOURCE_FILES = tuple('src/banto_ai/' + name + '.py' for name in (
    'anomaly_v03_preformal_parent_git_identity',
    'anomaly_v03_preformal_owned_source_git_session',
    'anomaly_v03_preformal_owned_git', 'anomaly_v03_preformal_owned_git_job',
    'anomaly_v03_preformal_job_tree_owner'))


def validate(entry, *, revision, roots):
    if entry is None:
        return None
    v.require(type(entry) is dict and set(entry) == {'path', 'expected_pin'},
              'parent Git identity policy entry')
    policy_path = Path(entry['path'])
    v.require(all(not policy_path.is_relative_to(root) and
                  not root.is_relative_to(policy_path.parent) for root in roots.values()),
              'parent Git identity policy separate from measured roots')
    policy = sessions._policy(policy_path, entry['expected_pin'], revision,
                              roots['outer'] / 'git-preflight-head')
    v.require(policy.get('process_ownership') == owned.JOB_OWNERSHIP,
              'parent Git identity requires private Job policy')
    return {'path': str(policy_path), 'expected_pin': copy.deepcopy(entry['expected_pin']),
            'policy': copy.deepcopy(policy), 'revision': revision}


def check(entry, *, phase, root, checkout_root, budget, receipts):
    v.require(phase in ('preflight', 'postflight'), 'parent Git identity phase')
    outputs = {}
    for operation in ('head', 'status'):
        call_id = 'git-' + phase + '-' + operation
        v.require(call_id not in receipts, 'parent Git identity call reused')
        budget.checkpoint(phase)
        # Keep the caller pin live through each call. Policy was checked before
        # any new measurement root, and the executor checks exe bytes again.
        sessions._policy(Path(entry['path']), entry['expected_pin'], entry['revision'],
                         root / call_id)
        checked = owned.run_owned(root=checkout_root, policy=entry['policy'],
            operation=operation, receipt_root=root / call_id, timeout_seconds=10,
            stop_probe=budget.probe)
        receipts[call_id] = copy.deepcopy(checked['receipt_pin'])
        budget.checkpoint(phase)
        receipt = checked['receipt']
        v.require(checked['receipt_root'] == str(root / call_id) and
                  receipt['operation'] == operation and receipt['source_path'] is None and
                  receipt['expected_output_pin'] is None and receipt['revision'] == entry['revision'] and
                  receipt['formal_permission'] is False and receipt['status'] == 'verified',
                  'parent Git identity receipt binding')
        saved = owned.verify_retained(root / call_id, receipts[call_id],
                                      root=checkout_root, policy=entry['policy'])
        v.require(saved['call_status'] == 'verified', 'parent Git identity saved call')
        saved_raw = observed._file(root / call_id / 'receipt.json', owned.MAX_RECEIPT)
        v.require(observed._pin(saved_raw) == receipts[call_id] and v.strict_json(saved_raw) == receipt,
                  'parent Git identity returned/saved receipt binding')
        raw = observed._file(root / call_id / 'stdout.bin', owned.MAX_OUTPUT[operation])
        v.require(type(checked['stdout']) is bytes and checked['stdout'] == raw and
                  observed._pin(raw) == receipt['stdout_pin'], 'parent Git identity stdout binding')
        outputs[operation] = raw
    v.require(outputs['head'].strip() == entry['revision'].encode() and not outputs['status'],
              'parent Git identity HEAD/clean differs')
    return outputs


def verify(entry, *, root, checkout_root, budget, receipts, phases=('preflight', 'postflight')):
    v.require(phases in (('preflight',), ('preflight', 'postflight')), 'parent Git identity verification phases')
    expected = {'git-' + phase + '-' + operation
                for phase in phases for operation in ('head', 'status')}
    v.require(set(receipts) == expected, 'parent Git identity exact four calls')
    for call_id, pin in receipts.items():
        budget.checkpoint(phases[-1])
        saved = owned.verify_retained(root / call_id, pin, root=checkout_root, policy=entry['policy'])
        v.require(saved['call_status'] == 'verified', 'parent Git identity final saved call')
        raw = observed._file(root / call_id / 'receipt.json', owned.MAX_RECEIPT)
        v.require(observed._pin(raw) == pin, 'parent Git identity final receipt pin')
        receipt = v.strict_json(raw)
        v.require(receipt['operation'] == call_id.rsplit('-', 1)[-1] and
                  receipt['revision'] == entry['revision'] and
                  receipt['job']['all_assigned_processes_exit_confirmed'] is True,
                  'parent Git identity final operation/Job binding')
    sessions._policy(Path(entry['path']), entry['expected_pin'], entry['revision'],
                     root / ('git-' + phases[-1] + '-head'), check_current=False)
