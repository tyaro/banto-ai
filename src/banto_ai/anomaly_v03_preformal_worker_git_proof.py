"""Bounded saved Git proof and opt-in verified lease completion.

The evidence reader must resolve original retained raw, never synthesize it from
the compact proof. Actual worker/archive wiring and native authentication remain
separate. No native API or raw cleanup is performed by this component.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03_preformal_worker_stop_channel as channel
from . import anomaly_v03_preformal_child_git_keeper as keepers

tree, v, io, observed, evidence = (
    keepers.tree, channel.v, channel.io, channel.observed, channel.evidence)
FORMAT = 'anomaly-v03-preformal-worker-git-proof-v1'
RAW_LIMITS = {'receipt.json':tree.direct.MAX_RECEIPT,
              'stdout.bin':max(tree.direct.MAX_OUTPUT.values()),
              'stderr.bin':tree.direct.MAX_STDERR, 'partial-archive.bin':512 * 1024}


class ProofVerifier:
    def __init__(self, *, endpoint, inventory_raw, inventory_pin, read_evidence):
        v.require(callable(read_evidence), 'Git proof original raw reader required')
        evidence._raw(inventory_raw, inventory_pin, 'Git proof caller-held inventory')
        v.require(type(inventory_raw) is bytes and len(inventory_raw) <= channel.MAX_CONTROL,
                  'Git proof inventory byte bound')
        inventory = v.strict_json(inventory_raw)
        v.require(io.json_bytes(inventory) == inventory_raw and type(inventory) is dict and
            set(inventory) == {'format','request_pin','revision','root','root_identity',
                'policy_pin','repository','calls','formal_permission'} and
            inventory['format'] == FORMAT+'-inventory' and inventory['formal_permission'] is False,
            'Git proof exact canonical inventory')
        self.endpoint, self.inventory = endpoint, inventory
        self.inventory_pin = copy.deepcopy(inventory_pin)
        self.read_evidence = read_evidence
        self._live()
        calls = inventory['calls']
        v.require(type(calls) is list and 0 < len(calls) <= channel.MAX_JOBS,
                  'Git proof bounded planned calls')
        for lease, call in enumerate(calls):
            v.require(type(call) is dict and set(call) == {'lease','phase','operation','source_path',
                'expected_output_pin','raw_inventory'} and type(call['lease']) is int and
                call['lease'] == lease and call['phase'] in ('pre','post'),
                'Git proof exact ordered call')
            tree.direct._command(endpoint._policy(), call['operation'],
                                 call['source_path'], call['expected_output_pin'])
            limits = call['raw_inventory']
            v.require(type(limits) is dict and {'receipt.json','stdout.bin','stderr.bin'} <= set(limits)
                <= set(RAW_LIMITS) and all(type(n) is int and 0 < n <= RAW_LIMITS[name]
                    for name,n in limits.items()) and
                limits['stdout.bin'] <= tree.direct.MAX_OUTPUT[call['operation']],
                'Git proof fixed original raw inventory and bounds')

    def _live(self):
        self.endpoint._live()
        request, inventory = self.endpoint.request, self.inventory
        v.require(all(inventory[key] == request[key] for key in
            ('revision','root','root_identity','policy_pin')) and
            inventory['request_pin'] == self.endpoint.request_pin,
            'Git proof request/revision/root/external policy link')
        repository = Path(inventory['repository'])
        v.require(repository.is_absolute() and repository == repository.resolve(),
                  'Git proof canonical repository')
        tree.paths.regular_path(repository, directory=True)

    def record(self, lease):
        v.require(type(lease) is int and 0 <= lease < len(self.inventory['calls']),
                  'Git proof planned lease')
        self._live()
        call = self.inventory['calls'][lease]
        packet = self.read_evidence(lease)
        v.require(type(packet) is dict and set(packet) == {'kind','raw','event'} and
                  packet['kind'] in ('receipt','recovery'), 'Git proof resolved original evidence')
        raw = packet['raw']
        v.require(type(raw) is dict and set(raw) == set(call['raw_inventory']),
                  'Git proof full retained raw inventory')
        pins = {}
        for name, maximum in call['raw_inventory'].items():
            value = raw[name]
            v.require(value is None or (type(value) is bytes and len(value) <= maximum),
                      'Git proof bounded retained raw bytes')
            v.require(value is not None or name in ('receipt.json','partial-archive.bin'),
                      'Git proof original stdout/stderr required')
            pins[name] = None if value is None else observed._pin(value)
        event = packet['event']
        if packet['kind'] == 'receipt':
            v.require(raw['receipt.json'] is not None and raw.get('partial-archive.bin') is None,
                      'Git proof full receipt without partial archive')
            tree.verify_quiescence(raw['receipt.json'], pins['receipt.json'], event,
                root=Path(self.inventory['repository']), policy=self.endpoint._policy(),
                stdout_raw=raw['stdout.bin'], stderr_raw=raw['stderr.bin'])
            receipt = v.strict_json(raw['receipt.json'])
            v.require(all(receipt[key] == call[key] for key in
                ('operation','source_path','expected_output_pin')),
                'Git proof retained receipt matches planned call')
            status = receipt['status']
            identity = {key:event['process_identity'][key] for key in
                        ('pid','creation_time_100ns','start_token')}
        else:
            # A keeper result is not a successful Git receipt. All partial raw
            # remains pinned, including a partial archive if planned beforehand.
            tree.direct._policy(Path(self.inventory['repository']), self.endpoint._policy())
            v.require(type(event) is dict and set(event) == {'format','process_identity','exit_code',
                'accounting','closed_handles','call_status','formal_permission','execution_authenticated',
                'lease_completed','failure_raw_verified','parent_ack_authorized'} and
                event['format'] == 'anomaly-v03-child-git-recovery-observation-v1' and
                event['call_status'] == 'failed' and all(event[key] is False for key in
                    ('formal_permission','execution_authenticated','lease_completed',
                     'failure_raw_verified','parent_ack_authorized')),
                'Git proof exact failed recovery observation')
            identity = channel._identity(event['process_identity'])
            account, handles = event['accounting'], event['closed_handles']
            v.require(type(event['exit_code']) is int and 0 <= event['exit_code'] < 2**32 and
                type(account) is dict and set(account) == {'total_processes','active_processes',
                    'limit_terminated_processes'} and all(type(n) is int and n >= 0 for n in account.values())
                and account['active_processes'] == 0 and
                account['limit_terminated_processes'] <= account['total_processes'] and
                type(handles) is dict and {'thread','process','job'} <= set(handles) <= {
                    'thread','process','job','inherited_0','inherited_1','inherited_2'} and
                all(type(n) is int and 0 < n < 2**64 for n in handles.values()) and
                len(set(handles.values())) == len(handles),
                'Git proof recovered original exit/empty/close consistency')
            status = 'failed'
        summary = {'call_pin':observed._pin(io.json_bytes(call)), 'kind':packet['kind'],
                   'raw_pins':pins, 'event':event, 'call_status':status}
        result = {'lease':lease,'kind':packet['kind'],'evidence_pin':observed._pin(io.json_bytes(summary))}
        return result, copy.deepcopy(identity), status, copy.deepcopy(event)

    def proof(self, records):
        self._live()
        binding, binding_pin = self.endpoint._binding()
        rows, identities, statuses = [], set(), []
        for lease, expected in enumerate(records):
            row, identity, status, _ = self.record(lease)
            v.require(row == expected and identity['start_token'] not in identities,
                      'Git proof saved raw changed or original identity reused')
            identities.add(identity['start_token']); statuses.append(status); rows.append(row)
        v.require(0 < len(rows) <= len(self.inventory['calls']) and
            all(status == 'verified' for status in statuses[:-1]) and
            (statuses[-1] == 'failed' or len(rows) == len(self.inventory['calls'])),
            'Git proof complete inventory or stopped failed prefix')
        result = {'format':FORMAT,'request_pin':self.endpoint.request_pin,
            'inventory_pin':self.inventory_pin,'binding_pin':binding_pin,
            'worker_identity':binding['worker_identity'],'records':rows,
            'terminal':'failed' if statuses[-1] == 'failed' else 'complete',
            'formal_permission':False}
        raw = io.json_bytes(result)
        v.require(len(raw) <= channel.MAX_CONTROL, 'Git proof compact byte bound')
        self._live()
        return raw

    def verify(self, raw, jobs_finished):
        v.require(type(raw) is bytes and len(raw) <= channel.MAX_CONTROL and
                  type(jobs_finished) is int, 'Git proof bounded raw and exact count')
        proof = v.strict_json(raw)
        v.require(type(proof) is dict and type(proof.get('records')) is list and
                  len(proof['records']) == jobs_finished and jobs_finished <= channel.MAX_JOBS,
                  'Git proof exact finished inventory count')
        return self.proof(proof['records']) == raw


class VerifiedLeases:
    def __init__(self, *, child, verifier):
        v.require(isinstance(child, channel.ChildChannel) and verifier.endpoint is child,
                  'Git proof original child endpoint')
        self.child, self.verifier = child, verifier
        self.records, self.kept = [], {}
        self.error = None

    def _failed(self, failure):
        self.child.stopped = True
        if self.error is None:
            self.error = failure

    def finish(self, lease, *, keeper=None):
        # Keep the exact keeper before reading raw or consulting a ledger.
        if keeper is not None:
            self.kept[lease] = keeper
        try:
            v.require(self.error is None and type(lease) is int and lease == len(self.records)
                and self.child.finished == len(self.records) and lease in self.child.active,
                'Git proof ordered active lease')
            row, _, status, event = self.verifier.record(lease)
            if row['kind'] == 'recovery':
                v.require(isinstance(keeper, keepers.ChildGitKeeper) and keeper.child is self.child
                    and keeper.lease == lease and self.child.owners.get(lease) is keeper.original
                    and keeper.completion is not None and not keeper.remaining and
                    not getattr(keeper.original,'attribute_list_cleanup_pending',False) and
                    not getattr(keeper.original,'unknown_close_handles',()) and
                    io.json_bytes(keeper.completion) == io.json_bytes(event) and
                    keeper.closed == keeper.initial_handles == event['closed_handles'],
                    'Git proof exact reconciled keeper required before release')
            else:
                v.require(keeper is None and lease not in self.child.owners,
                          'Git proof receipt cannot release retained original owner')
            if status == 'failed':
                self.child.stopped = True
            # Reread raw before the metadata transition. No owner/raw is discarded
            # if this check, ledger transition, or later proof publication fails.
            v.require(self.verifier.record(lease)[0] == row, 'Git proof raw changed before lease finish')
            self.records.append(row)
            self.child.finish_job(lease, exit_confirmed=True, handles_closed=True, raw_preserved=True)
            return copy.deepcopy(row)
        except BaseException as failure:
            self._failed(failure)
            if keeper is not None:
                keeper.original.proof_adapter = self
            raise

    def acknowledge(self):
        self.child.stopped = True
        try:
            v.require(self.error is None and not self.child.active and not self.child.owners and
                      self.child.finished == len(self.records), 'Git proof no unresolved owner/ledger')
            raw = self.verifier.proof(self.records)
            path = self.child.root / 'git-proof.json'
            pin = channel._write(path, v.strict_json(raw))
            return self.child.acknowledge({'path':str(path),'pin':pin})
        except BaseException as failure:
            self._failed(failure)
            raise
