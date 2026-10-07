"""Bounded worker Git raw/event storage; no process launch or lease release.

Caller-held manifest/inventory pins bind the saved resolver to original raw.
Failed appends retain the partial archive and pending packet and forbid reuse.
Actual worker, owner lifetime, cache and common-budget wiring are separate.
"""
from __future__ import annotations

import base64
import copy
import gzip
import os
from pathlib import Path

from . import anomaly_v03_preformal_worker_git_proof as proof
from . import anomaly_v03_preformal_git_receipt_archive as bounds

v, io, observed, evidence, paths = proof.v, proof.io, proof.observed, proof.evidence, proof.tree.paths
FORMAT = 'anomaly-v03-preformal-worker-git-archive-v1'
MAGIC = b'WGA1'
MAX_BYTES, MAX_RECORD, MAX_RAW = bounds.MAX_BYTES, bounds.MAX_RECORD, bounds.MAX_RAW


def _path(path, endpoint):
    path = Path(path)
    root = Path(endpoint.request['budget_root'])
    v.require(proof.channel._inside(path, root) and path.name == 'worker-git.bin' and
        len(path.relative_to(root).parts) <= 2, 'worker archive fixed measured path/depth')
    paths.regular_path(path.parent, directory=True)
    paths.regular_path(path, missing=True)
    return path


def _inventory(verifier):
    raw = io.json_bytes(verifier.inventory)
    evidence._raw(raw, verifier.inventory_pin, 'worker archive held inventory')
    calls = verifier.inventory['calls']
    v.require(all(call['raw_inventory']['stdout.bin'] <= bounds.MAX_STDOUT for call in calls) and
        not any(a['phase'] == 'post' and b['phase'] == 'pre' for a,b in zip(calls,calls[1:])),
        'worker archive existing stdout bound and ordered phases')
    return raw


def _append_frame(path, frame):
    with path.open('ab') as stream:
        written = stream.write(frame)
        v.require(written == len(frame), 'worker archive full append')
        stream.flush()
        os.fsync(stream.fileno())


class SavedWorkerGitArchive:
    def __init__(self, *, endpoint, manifest_raw, manifest_pin, inventory_raw,
                 inventory_pin, checkpoint):
        v.require(callable(checkpoint) and type(manifest_raw) is bytes and
            len(manifest_raw) <= proof.channel.MAX_CONTROL, 'worker archive bounded held manifest')
        evidence._raw(manifest_raw, manifest_pin, 'worker archive external manifest pin')
        manifest = v.strict_json(manifest_raw)
        v.require(io.json_bytes(manifest) == manifest_raw and type(manifest) is dict and
            set(manifest) == {'format','path','archive_pin','inventory_pin','rows','formal_permission'} and
            manifest['format'] == FORMAT+'-manifest' and manifest['formal_permission'] is False and
            manifest['inventory_pin'] == inventory_pin, 'worker archive exact manifest/context')
        self.endpoint, self.checkpoint, self.manifest = endpoint, checkpoint, manifest
        self.path = _path(manifest['path'], endpoint)
        rows = manifest['rows']
        v.require(type(rows) is list and 0 < len(rows) <= proof.channel.MAX_JOBS,
                  'worker archive bounded nonempty rows')
        self._packets = []
        self.verifier = proof.ProofVerifier(endpoint=endpoint, inventory_raw=inventory_raw,
            inventory_pin=inventory_pin, read_evidence=lambda lease:copy.deepcopy(self._packets[lease]))
        _inventory(self.verifier)
        v.require(len(rows) <= len(self.verifier.inventory['calls']), 'worker archive planned call count')
        raw = self._current(); offset = 0
        for lease,row in enumerate(rows):
            v.require(type(row) is dict and set(row) == {'lease','offset','bytes','sha256','evidence_pin'} and
                type(row['lease']) is int and row['lease'] == lease and type(row['offset']) is int and
                row['offset'] == offset and type(row['bytes']) is int and 8 <= row['bytes'] <= MAX_RECORD+8
                and offset+row['bytes'] <= len(raw), 'worker archive exact ordered frame coverage')
            frame = raw[offset:offset+row['bytes']]
            evidence._raw(frame, {'bytes':row['bytes'],'sha256':row['sha256']}, 'worker archive frame pin')
            v.require(frame[:4] == MAGIC and int.from_bytes(frame[4:8],'big') == len(frame)-8,
                      'worker archive magic/length')
            decoded = bounds._gunzip(frame[8:], MAX_RAW)
            record = v.strict_json(decoded)
            v.require(io.json_bytes(record) == decoded and type(record) is dict and set(record) == {
                'format','lease','inventory_pin','kind','raw_b64','event'} and record['format'] == FORMAT and
                type(record['lease']) is int and record['lease'] == lease and
                record['inventory_pin'] == inventory_pin, 'worker archive canonical bound record')
            call = self.verifier.inventory['calls'][lease]
            encoded = record['raw_b64']
            v.require(type(encoded) is dict and set(encoded) == set(call['raw_inventory']),
                      'worker archive exact original raw names')
            packet_raw = {name:None if value is None else bounds._decode(value,call['raw_inventory'][name])
                          for name,value in encoded.items()}
            self._packets.append({'kind':record['kind'],'raw':packet_raw,'event':record['event']})
            offset += row['bytes']
        v.require(offset == len(raw), 'worker archive no trailing/partial frame')
        identities, statuses = set(), []
        for lease,row in enumerate(rows):
            checked, identity, status, _ = self.verifier.record(lease)
            v.require(checked['evidence_pin'] == row['evidence_pin'] and
                identity['start_token'] not in identities, 'worker archive raw/event pin and unique original identity')
            identities.add(identity['start_token']); statuses.append(status)
        v.require(all(status == 'verified' for status in statuses[:-1]),
                  'worker archive no call after failed recovery/receipt')
        self.statuses = statuses
        self._current()
        self.verifier.read_evidence = self.read

    def _current(self):
        self.checkpoint(); self.endpoint._live()
        raw = observed._file(self.path, MAX_BYTES)
        evidence._raw(raw, self.manifest['archive_pin'], 'worker archive caller-held complete raw pin')
        self.checkpoint()
        return raw

    def read(self, lease):
        v.require(type(lease) is int and 0 <= lease < len(self._packets), 'worker archive saved lease')
        self._current()
        return copy.deepcopy(self._packets[lease])


class WorkerGitArchive:
    def __init__(self, *, path, verifier, checkpoint):
        v.require(callable(checkpoint), 'worker archive shared budget checkpoint required')
        self.verifier, self.checkpoint = verifier, checkpoint
        self.inventory_raw = _inventory(verifier)
        self.path = _path(path, verifier.endpoint)
        v.require(not self.path.exists(), 'worker archive exclusive unused file')
        self.rows, self.raw, self.statuses = [], b'', []
        self.pending, self.failed = None, False
        checkpoint(); verifier._live()
        io._exclusive(self.path, b'')
        checkpoint()

    def _manifest(self, raw, rows):
        result = {'format':FORMAT+'-manifest','path':str(self.path),'archive_pin':observed._pin(raw),
            'inventory_pin':self.verifier.inventory_pin,'rows':rows,'formal_permission':False}
        encoded = io.json_bytes(result)
        v.require(len(encoded) <= proof.channel.MAX_CONTROL, 'worker archive compact manifest byte bound')
        return encoded

    def append(self, lease):
        try:
            v.require(not self.failed and type(lease) is int and lease == len(self.rows) and
                len(self.rows) < proof.channel.MAX_JOBS and
                (not self.statuses or self.statuses[-1] == 'verified'), 'worker archive active ordered append')
            self.pending = {'lease':lease}
            self.checkpoint(); self.verifier._live()
            v.require(observed._file(self.path,MAX_BYTES) == self.raw, 'worker archive previous bytes changed')
            checked, _, status, _ = self.verifier.record(lease)
            packet = copy.deepcopy(self.verifier.read_evidence(lease))
            self.pending.update(packet=packet, evidence_pin=copy.deepcopy(checked['evidence_pin']))
            snapshot = proof.ProofVerifier(endpoint=self.verifier.endpoint, inventory_raw=self.inventory_raw,
                inventory_pin=self.verifier.inventory_pin, read_evidence=lambda _:packet)
            v.require(snapshot.record(lease)[0] == checked, 'worker archive original raw changed before append')
            record = {'format':FORMAT,'lease':lease,'inventory_pin':self.verifier.inventory_pin,
                'kind':packet['kind'],'event':packet['event'],'raw_b64':{
                    name:None if value is None else base64.b64encode(value).decode('ascii')
                    for name,value in packet['raw'].items()}}
            encoded = io.json_bytes(record)
            v.require(len(encoded) <= MAX_RAW, 'worker archive decoded record byte bound')
            compressed = gzip.compress(encoded,mtime=0)
            v.require(len(compressed) <= MAX_RECORD, 'worker archive compressed record byte bound')
            frame = MAGIC+len(compressed).to_bytes(4,'big')+compressed
            candidate = self.raw+frame
            v.require(len(candidate) <= MAX_BYTES, 'worker archive existing total byte bound')
            row = {'lease':lease,'offset':len(self.raw),**observed._pin(frame),
                   'evidence_pin':copy.deepcopy(checked['evidence_pin'])}
            rows = self.rows+[row]
            manifest = self._manifest(candidate,rows)
            self.failed = True  # No append retry after any uncertain write/readback.
            self.checkpoint(); _append_frame(self.path,frame)
            saved = SavedWorkerGitArchive(endpoint=self.verifier.endpoint,
                manifest_raw=manifest,manifest_pin=observed._pin(manifest),
                inventory_raw=self.inventory_raw,inventory_pin=self.verifier.inventory_pin,
                checkpoint=self.checkpoint)
            v.require(saved.read(lease) == packet and self.verifier.record(lease)[0] == checked,
                      'worker archive saved/original raw readback')
            self.checkpoint()
            self.raw, self.rows = candidate, rows
            self.statuses.append(status)
            self.failed, self.pending = False, None
            return copy.deepcopy(checked)
        except BaseException:
            self.failed = True
            raise

    def manifest(self):
        v.require(not self.failed and self.rows, 'worker archive verified nonempty manifest')
        self.checkpoint(); self.verifier._live()
        v.require(observed._file(self.path,MAX_BYTES) == self.raw, 'worker archive final raw changed')
        raw = self._manifest(self.raw,self.rows)
        self.checkpoint()
        return raw, observed._pin(raw)
