"""Bounded worker Git raw/event storage; no process launch or lease release.

Caller-held manifest/inventory pins bind the saved resolver to original raw.
Failed appends retain the partial archive and pending packet and forbid reuse.
Actual worker, owner lifetime, cache and common-budget wiring are separate.
"""
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import os
from pathlib import Path

from . import anomaly_v03_preformal_worker_git_proof as proof
from . import anomaly_v03_preformal_git_receipt_archive as bounds

v, io, observed, evidence, paths = proof.v, proof.io, proof.observed, proof.evidence, proof.tree.paths
FORMAT = 'anomaly-v03-preformal-worker-git-archive-v1'
MAGIC = b'WGA1'
MAX_BYTES, MAX_RECORD, MAX_RAW = bounds.MAX_BYTES, bounds.MAX_RECORD, bounds.MAX_RAW
APPEND_PLAN_FORMAT = 'anomaly-v03-preformal-worker-git-append-plan-v1'


class PacketPartitionPreparation:
    """Memory-only new-format codec contract, never native or lease admission.

    The caller keeps this object and its original owner before prepare/readback.
    No legacy archive, raw path, stream, HANDLE or receipt is written or closed.
    Payload bounds exclude object/transient/RSS and other writers' memory.
    """
    FORMAT = 'anomaly-v03-worker-git-packet-partition-preparation-v1'
    MAGIC, CHUNK_BYTES, ENCODED_BYTES, FRAME_COUNT = b'WGP2', 32768, 65536, 64
    CONTEXT_FIELDS = {'request_pin','inventory_pin','revision','root','root_identity','lease'}

    def __init__(self, *, owner, checkpoint, context, packet, raw_limits):
        self.original_owner, self.original_checkpoint = owner, checkpoint
        self.original_context, self.original_packet, self.original_limits = context, packet, raw_limits
        self.pending, self.error, self.result = None, None, None
        self._inputs = (owner, checkpoint, context, packet, raw_limits)
        self._failure, self._completed, self._started = None, None, False
        self.retained, self.rejected = [], []
        self._codec=(gzip.compress,base64.b64encode,bounds._gunzip,bounds._decode)
        self._pending_anchor=None;self._completion_anchor=None
        self._records=();self._raw_returns=()
        self._record_bindings=();self._readback_owners=()

    def _failed(self, error):
        if self._failure is None:self._failure = error
        self.error = self._failure
        raise self._failure

    def _fixed(self):
        owner, checkpoint, context, packet, limits = self._inputs
        v.require(self.original_owner is owner and self.original_checkpoint is checkpoint and
            self.original_context is context and self.original_packet is packet and
            self.original_limits is limits, 'partition original owner/input reference changed')
        v.require((gzip.compress,base64.b64encode,bounds._gunzip,bounds._decode)==self._codec and
            (self.FORMAT,self.MAGIC,self.CHUNK_BYTES,self.ENCODED_BYTES,self.FRAME_COUNT)==(
                'anomaly-v03-worker-git-packet-partition-preparation-v1',b'WGP2',32768,65536,64) and
            type(self.retained) is list and tuple(self.retained)==self._records,
            'partition original codec/closed bounds/retention changed')
        v.require(all(set(row)=={n for n,_ in pairs} and all(row[n] is value for n,value in pairs)
            for row,pairs in self._record_bindings) and type(self.rejected) is list and
            len(self.rejected)==len(self._readback_owners) and
            all(row is held[0] and row.get('frames') is held[1] and row.get('manifest_raw') is held[2] and
                row.get('manifest_pin') is held[3] for row,held in zip(self.rejected,self._readback_owners)) and
            all('encoded' not in row or io.json_bytes(row['record'])==row['encoded'] for row in self._records),
            'partition original returned buffer/incoming owner metadata changed')
        if self._started and self._completed is None:
            v.require(self.pending is self._pending_anchor and
                self.pending.get('context') is context and self.pending.get('packet') is packet and
                self.pending.get('limits') is limits,'partition original pending owner changed')
        if self._completed is not None:
            held = self._completed
            context_raw,limits_raw,frames,manifest_raw,manifest_pin_raw,frame_pins,identity_raw=self._completion_anchor
            v.require(self.result is held and self.pending is None and
                held['context_raw'] is context_raw and held['limits_raw'] is limits_raw and
                io.json_bytes(context)==context_raw and io.json_bytes(limits)==limits_raw and
                packet==held['packet'] and held['frames'] is frames and held['frame_objects'] is frames and
                held['manifest_raw'] is manifest_raw and io.json_bytes(held['manifest_pin'])==manifest_pin_raw and
                held['frame_pins']==frame_pins and
                io.json_bytes({'kind':held['packet']['kind'],'event':held['packet']['event'],'raw_pins':{
                    n:None if r is None else observed._pin(r) for n,r in held['packet']['raw'].items()}})==identity_raw,
                'partition original completion changed')
            evidence._raw(held['manifest_raw'],held['manifest_pin'],'partition original manifest changed')
            v.require(tuple(observed._pin(frame) for frame in held['frames'])==held['frame_pins'],
                'partition original frame bytes changed')

    def _clock(self):
        self._fixed(); self.original_checkpoint(); self._fixed()

    def _frame(self, record):
        held={'record':record};self.retained.append(held);self._records+=(held,)
        self._record_bindings+=((held,(('record',record),)),)
        held['encoded']=encoded=io.json_bytes(record)
        self._raw_returns+=(encoded,)
        self._record_bindings=self._record_bindings[:-1]+((held,self._record_bindings[-1][1]+(('encoded',encoded),)),)
        v.require(len(encoded)<=self.ENCODED_BYTES,'partition decoded chunk byte bound')
        self._clock()
        held['compressed']=compressed=self._codec[0](encoded,mtime=0)
        self._raw_returns+=(compressed,)
        self._record_bindings=self._record_bindings[:-1]+((held,self._record_bindings[-1][1]+(('compressed',compressed),)),)
        v.require(type(compressed) is bytes and len(compressed)<=MAX_RECORD,
            'partition compressed chunk byte bound')
        held['frame']=frame=self.MAGIC+len(compressed).to_bytes(4,'big')+compressed
        self._raw_returns+=(frame,)
        self._record_bindings=self._record_bindings[:-1]+((held,self._record_bindings[-1][1]+(('frame',frame),)),)
        self._clock();return frame

    def prepare(self):
        if self._failure is not None:raise self._failure
        if self._completed is not None:return self.view()
        try:
            v.require(not self._started,'partition preparation cannot replay')
            self._started=True
            self.pending=self._pending_anchor={'context':self.original_context,'packet':self.original_packet,'limits':self.original_limits}
            self._fixed()
            v.require(self.original_owner is not None and callable(self.original_checkpoint),
                'partition caller-held owner and shared checkpoint')
            context,packet,limits=self.original_context,self.original_packet,self.original_limits
            v.require(type(context) is dict and set(context)==self.CONTEXT_FIELDS and
                type(context['lease']) is int and 0<=context['lease']<proof.channel.MAX_JOBS and
                type(context['root_identity']) is list and len(context['root_identity'])==2 and
                all(type(n) is int and n>=0 for n in context['root_identity']), 'partition exact context')
            evidence._digest(context['revision'],40)
            evidence._pin(context['request_pin']);evidence._pin(context['inventory_pin'])
            root=Path(context['root'])
            v.require(root.is_absolute() and str(root)==str(root.resolve()),'partition canonical held root')
            context_raw=io.json_bytes(context);context_pin=observed._pin(context_raw)
            self.pending.update(context_raw=context_raw,context_pin=context_pin)
            v.require(len(context_raw)<=proof.channel.MAX_CONTROL,'partition context bytes')
            v.require(type(packet) is dict and set(packet)=={'kind','event','raw'} and
                packet['kind'] in ('receipt','recovery') and type(packet['raw']) is dict and
                type(limits) is dict and set(packet['raw'])==set(limits) and
                {'receipt.json','stdout.bin','stderr.bin'}<=set(limits)<=set(proof.RAW_LIMITS),
                'partition full original raw names')
            v.require(all(type(n) is int and 0<n<=proof.RAW_LIMITS[name] for name,n in limits.items()),
                'partition independent original raw maxima')
            limits_raw=io.json_bytes(limits);snapshot=copy.deepcopy(packet)
            self.pending.update(limits_raw=limits_raw,packet_snapshot=snapshot)
            event_raw=io.json_bytes(snapshot['event'])
            v.require(len(event_raw)<=proof.channel.MAX_CONTROL,'partition event bytes')
            raw_pins={}
            for name,value in snapshot['raw'].items():
                v.require(value is None or (type(value) is bytes and len(value)<=limits[name]),
                    'partition original raw cap')
                v.require(value is not None or name in ('receipt.json','partial-archive.bin'),
                    'partition stdout/stderr original raw required')
                raw_pins[name]=None if value is None else observed._pin(value)
            identity={'kind':snapshot['kind'],'event':snapshot['event'],'raw_pins':raw_pins}
            identity_raw=io.json_bytes(identity);packet_pin=observed._pin(identity_raw);frames=[];rows=[];growth=0
            self.pending.update(packet_pin=packet_pin,frames=frames,rows=rows)
            self._clock()
            for name in sorted(snapshot['raw']):
                value=snapshot['raw'][name]
                if value is None:continue
                offsets=range(0,len(value),self.CHUNK_BYTES) if value else (0,)
                for offset in offsets:
                    v.require(len(frames)<self.FRAME_COUNT,'partition chunk count bound')
                    chunk=value[offset:offset+self.CHUNK_BYTES]
                    record={'format':self.FORMAT,'context_pin':context_pin,'packet_pin':packet_pin,
                        'name':name,'offset':offset,'total_bytes':len(value),'raw_b64':self._codec[1](chunk).decode('ascii')}
                    frame=self._frame(record);frames.append(frame);growth+=len(frame)
                    v.require(growth<=MAX_BYTES,'partition independent new archive growth bound')
                    rows.append({'name':name,'offset':offset,'raw_bytes':len(chunk),'frame_pin':observed._pin(frame)})
            manifest={'format':self.FORMAT+'-manifest','context':copy.deepcopy(context),'context_pin':context_pin,
                'packet':identity,'packet_pin':packet_pin,'raw_limits':copy.deepcopy(limits),'rows':rows,
                'archive_growth_bytes':growth,'formal_permission':False}
            self.pending['manifest_raw']=manifest_raw=io.json_bytes(manifest)
            v.require(len(manifest_raw)<=proof.channel.MAX_CONTROL,'partition manifest byte bound')
            self._clock()
            v.require(packet==snapshot and io.json_bytes(context)==context_raw and io.json_bytes(limits)==limits_raw,
                'partition caller input changed during codec')
            frame_tuple=tuple(frames)
            held={'packet':snapshot,'context_raw':context_raw,'limits_raw':limits_raw,'frames':frame_tuple,
                'frame_objects':frame_tuple,'frame_pins':tuple(observed._pin(f) for f in frames),
                'manifest_raw':manifest_raw,'manifest_pin':observed._pin(manifest_raw)}
            self._completion_anchor=(context_raw,limits_raw,frame_tuple,manifest_raw,
                io.json_bytes(held['manifest_pin']),held['frame_pins'],identity_raw)
            self._completed=self.result=held;self.pending=None
            return self.view()
        except BaseException as error:self._failed(error)

    def view(self):
        if self._failure is not None:raise self._failure
        try:
            self._fixed();v.require(self._completed is not None,'partition completed preparation required')
            held=self._completed
            return {'frames':held['frames'],'manifest_raw':held['manifest_raw'],
                'manifest_pin':copy.deepcopy(held['manifest_pin']),'native_authorized':False,
                'atomic_reservation':False,'capacity_pass':False,'lease_completed':False,
                'parent_ack_authorized':False,'execution_authenticated':False}
        except BaseException as error:self._failed(error)

    def readback(self, *, frames, manifest_raw, manifest_pin):
        if self._failure is not None:raise self._failure
        held={'frames':frames,'manifest_raw':manifest_raw,'manifest_pin':manifest_pin}
        self._readback_owners+=((held,frames,manifest_raw,manifest_pin),)
        self.rejected.append(held)  # Incoming original bytes before clock/decode/validation.
        try:
            self._clock();view=self.view()
            v.require(type(frames) is tuple and type(manifest_raw) is bytes and
                len(manifest_raw)<=proof.channel.MAX_CONTROL and manifest_pin==view['manifest_pin'] and
                manifest_raw==view['manifest_raw'],'partition external original manifest pin')
            evidence._raw(manifest_raw,manifest_pin,'partition full manifest raw')
            manifest=v.strict_json(manifest_raw);rows=manifest['rows']
            v.require(len(frames)==len(rows)<=self.FRAME_COUNT and
                sum(len(f) for f in frames)==manifest['archive_growth_bytes']<=MAX_BYTES,
                'partition complete frame coverage and archive growth')
            values={name:None if p is None else bytearray() for name,p in manifest['packet']['raw_pins'].items()}
            held['raw_buffers']=values
            for frame,row in zip(frames,rows):
                self._clock()
                v.require(type(frame) is bytes and 8<=len(frame)<=MAX_RECORD+8 and frame[:4]==self.MAGIC and
                    int.from_bytes(frame[4:8],'big')==len(frame)-8,'partition exact new frame header')
                evidence._raw(frame,row['frame_pin'],'partition original frame pin')
                decoded=self._codec[2](frame[8:],self.ENCODED_BYTES);held['decoded']=decoded
                record=v.strict_json(decoded)
                v.require(io.json_bytes(record)==decoded and type(record) is dict and set(record)=={
                    'format','context_pin','packet_pin','name','offset','total_bytes','raw_b64'} and
                    record['format']==self.FORMAT and record['context_pin']==manifest['context_pin'] and
                    record['packet_pin']==manifest['packet_pin'] and record['name']==row['name'] and
                    type(record['offset']) is int and record['offset']==row['offset'], 'partition exact bound chunk')
                target=values[row['name']]
                v.require(target is not None and len(target)==row['offset'],'partition original ordered raw coverage')
                chunk=self._codec[3](record['raw_b64'],self.CHUNK_BYTES);held['chunk']=chunk
                raw_pin=manifest['packet']['raw_pins'][row['name']]
                v.require(len(chunk)==row['raw_bytes'] and type(record['total_bytes']) is int and
                    record['total_bytes']==raw_pin['bytes'] and len(target)+len(chunk)<=raw_pin['bytes'],
                    'partition no duplicated or overlapping raw chunk')
                target.extend(chunk)
            raw={name:None if value is None else bytes(value) for name,value in values.items()};held['readback_raw']=raw
            for name,value in raw.items():
                expected=manifest['packet']['raw_pins'][name]
                v.require(value is None if expected is None else observed._pin(value)==expected,
                    'partition full original raw readback pin')
            packet={'kind':manifest['packet']['kind'],'event':copy.deepcopy(manifest['packet']['event']),'raw':raw}
            v.require(packet==self._completed['packet'],'partition readback original packet')
            self._clock();return packet
        except BaseException as error:self._failed(error)

    def execute(self):
        if self._failure is not None:raise self._failure
        raise ValueError('partition native/archive IO admission not prepared')


_PARTITION_PREPARATION_TYPE = PacketPartitionPreparation


class PartitionedArchivePreparation:
    """All planned packet payload maxima and original readback, with no IO.

    This is not an atomic reservation, native owner observation, whole runtime
    capacity proof or lease/ack authority. All failure raw remains caller-held.
    """
    FORMAT = 'anomaly-v03-partitioned-archive-preparation-v1'

    def __init__(self, *, owner, checkpoint, allocation):
        self.original_owner,self.original_checkpoint,self.original_allocation=owner,checkpoint,allocation
        self._inputs=(owner,checkpoint,allocation);self._prepared=None;self._failure=None
        self.pending,self.error=None,None;self.completed=[];self._ledger=self._ledger_anchor=();self._pending=None;self._pending_input=None
        self.rejected=[];self._owners=();self._returns=();self._return_bindings=()
        self._prepared_anchor=None;self._bundle=None;self._bundle_anchor=None
        self.incoming=[];self._incoming=()

    @staticmethod
    def _packet_raw(packet):
        return io.json_bytes({'kind':packet['kind'],'event':packet['event'],'raw_pins':{
            name:None if raw is None else observed._pin(raw) for name,raw in packet['raw'].items()}})

    def _failed(self,error):
        if self._failure is None:self._failure=error
        self.error=self._failure;raise self._failure

    def _fixed(self):
        owner,checkpoint,allocation=self._inputs
        v.require(self.original_owner is owner and self.original_checkpoint is checkpoint and
            self.original_allocation is allocation and self.FORMAT=='anomaly-v03-partitioned-archive-preparation-v1',
            'partition archive original owner/allocation changed')
        if self._prepared is not None:
            v.require(self._prepared is self._prepared_anchor[0] and
                io.json_bytes(allocation)==self._prepared[0] and
                io.json_bytes(self._prepared[4])==self._prepared_anchor[1], 'partition archive caller allocation changed')
        v.require(self._ledger is self._ledger_anchor and type(self.completed) is list and len(self.completed)==len(self._ledger) and
            all(row is held[0] and io.json_bytes(row)==held[1] for row,held in zip(self.completed,self._ledger)),
            'partition archive completed prefix changed')
        v.require(type(self.rejected) is list and len(self.rejected)==len(self._owners) and
            all(row is held[0] and row.get('preparation') is held[1] for row,held in zip(self.rejected,self._owners)),
            'partition archive original incoming owner hidden')
        v.require(self.pending is self._pending,'partition archive pending owner hidden')
        if self._pending_input is not None:
            key,value=self._pending_input
            v.require(self._pending.get(key) is value,'partition archive pending input hidden')
        for held,original_view,frames,raw,pin_raw,packet,packet_raw in self._return_bindings:
            view=held['view']
            v.require(view is original_view and view['frames'] is frames and view['manifest_raw'] is raw and
                io.json_bytes(view['manifest_pin'])==pin_raw and
                (packet is None or held['readback'] is packet and self._packet_raw(packet)==packet_raw),
                'partition archive original returned view/readback changed')
        for held in self._ledger:
            view=held[2].view()
            v.require(view['manifest_raw'] is held[3] and view['frames'] is held[4],
                'partition archive original registered bytes changed')
        if self._bundle_anchor is not None:
            bundle,pin_raw=self._bundle_anchor
            v.require(self._bundle is bundle and io.json_bytes(bundle[2])==pin_raw,
                'partition archive original bundle changed')
        v.require(type(self.incoming) is list and len(self.incoming)==len(self._incoming) and
            all(row is held[0] and row.get('archive_raw') is held[1] and row.get('manifest_raw') is held[2] and
                row.get('manifest_pin') is held[3] for row,held in zip(self.incoming,self._incoming)),
            'partition archive original incoming bytes hidden')

    def _clock(self):
        self._fixed();self.original_checkpoint();self._fixed()

    def prepare(self):
        if self._failure is not None:raise self._failure
        try:
            self._fixed()
            if self._prepared is not None:return self.plan()
            self.pending=self._pending={'allocation':self.original_allocation}
            self._pending_input=('allocation',self.original_allocation)
            v.require(self.original_owner is not None and callable(self.original_checkpoint),
                'partition archive caller owner/shared clock')
            value=self.original_allocation
            v.require(type(value) is dict and set(value)=={'format','context','call_growth_maxima','archive_max_bytes','formal_permission'} and
                value['format']==self.FORMAT and value['formal_permission'] is False,
                'partition archive exact closed allocation')
            context=value['context'];maxima=value['call_growth_maxima'];maximum=value['archive_max_bytes']
            v.require(type(context) is dict and set(context)==PacketPartitionPreparation.CONTEXT_FIELDS-{'lease'} and
                type(maxima) is list and 0<len(maxima)<=proof.channel.MAX_JOBS and
                all(type(n) is int and 0<n<=MAX_BYTES for n in maxima) and
                type(maximum) is int and 0<maximum<=MAX_BYTES and sum(maxima)<=maximum,
                'partition archive all future call maxima before codec')
            evidence._digest(context['revision'],40);evidence._pin(context['request_pin']);evidence._pin(context['inventory_pin'])
            v.require(type(context['root_identity']) is list and len(context['root_identity'])==2 and
                all(type(n) is int and n>=0 for n in context['root_identity']), 'partition archive original root identity')
            root=Path(context['root']);v.require(root.is_absolute() and str(root)==str(root.resolve()),'partition archive canonical root')
            raw=io.json_bytes(value);self.pending['allocation_raw']=raw
            v.require(len(raw)<=proof.channel.MAX_CONTROL,'partition archive allocation bytes')
            self._prepared=(raw,io.json_bytes(context),tuple(maxima),maximum,observed._pin(raw))
            self._prepared_anchor=(self._prepared,io.json_bytes(self._prepared[4]))
            self._clock();self.pending=self._pending=self._pending_input=None;return self.plan()
        except BaseException as error:self._failed(error)

    def plan(self):
        if self._failure is not None:raise self._failure
        try:
            self._fixed();v.require(self._prepared is not None,'partition archive original allocation required')
            return {'allocation_pin':copy.deepcopy(self._prepared[4]),'planned_calls':len(self._prepared[2]),
                'reserved_maxima_bytes':sum(self._prepared[2]),'actual_growth_bytes':sum(row['growth_bytes'] for row in self.completed),
                'atomic_reservation':False,'capacity_pass':False,'native_authorized':False,'lease_completed':False,
                'parent_ack_authorized':False,'execution_authenticated':False}
        except BaseException as error:self._failed(error)

    def register(self,preparation):
        if self._failure is not None:raise self._failure
        held={'preparation':preparation};self.rejected.append(held);self._owners+=((held,preparation),)
        try:
            v.require(self._pending is None,'partition archive original pending cannot be replaced')
            self.pending=self._pending=held;self._pending_input=('preparation',preparation);self._clock()
            v.require(self._prepared is not None and self._bundle is None and
                len(self.completed)<len(self._prepared[2]) and type(preparation) is _PARTITION_PREPARATION_TYPE,
                'partition archive ordered original packet preparation')
            lease=len(self.completed);context={**v.strict_json(self._prepared[1]),'lease':lease}
            v.require(preparation.original_owner is self.original_owner and
                preparation.original_checkpoint is self.original_checkpoint and preparation.original_context==context,
                'partition archive same original owner/clock/request/root/inventory/lease')
            if self._ledger:
                v.require(self._ledger[-1][5]['kind']!='recovery','partition archive no packet after recovery prefix')
            held['view']=view=preparation.view();self._returns+=(view,)
            binding=(held,view,view['frames'],view['manifest_raw'],io.json_bytes(view['manifest_pin']),None,None)
            self._return_bindings+=(binding,)
            held['readback']=packet=preparation.readback(frames=view['frames'],manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
            self._returns+=(packet,)
            packet_raw=self._packet_raw(packet)
            self._return_bindings=self._return_bindings[:-1]+(binding[:5]+(packet,packet_raw),)
            self._fixed()
            v.require(packet==preparation.original_packet,'partition archive original full readback packet')
            growth=sum(len(f) for f in view['frames']);held['growth_bytes']=growth
            v.require(growth<=self._prepared[2][lease] and sum(row['growth_bytes'] for row in self.completed)+growth<=self._prepared[3],
                'partition archive original call and total growth maxima')
            row={'lease':lease,'offset':sum(row['growth_bytes'] for row in self.completed),'growth_bytes':growth,
                'packet_manifest_pin':copy.deepcopy(view['manifest_pin'])}
            self._clock();self.completed.append(row)
            self._ledger+=((row,io.json_bytes(row),preparation,view['manifest_raw'],view['frames'],packet),)
            self._ledger_anchor=self._ledger
            self.pending=self._pending=self._pending_input=None;return self.plan()
        except BaseException as error:self._failed(error)

    def bundle(self):
        if self._failure is not None:raise self._failure
        try:
            self._fixed();v.require(self._prepared is not None and len(self._ledger)==len(self._prepared[2])>0,
                'partition archive full planned-call coverage before bundle')
            if self._bundle is None:
                raw=b''.join(frame for held in self._ledger for frame in held[4]);self._returns+=(raw,)
                manifest={'format':self.FORMAT+'-manifest','allocation_pin':self._prepared[4],
                    'archive_pin':observed._pin(raw),'packets':copy.deepcopy(self.completed),'formal_permission':False}
                encoded=io.json_bytes(manifest);self._returns+=(encoded,)
                v.require(len(raw)<=self._prepared[3] and len(encoded)<=proof.channel.MAX_CONTROL,
                    'partition archive complete payload/manifest bounds')
                self._bundle=(raw,encoded,observed._pin(encoded))
                self._bundle_anchor=(self._bundle,io.json_bytes(self._bundle[2]))
            return {'archive_raw':self._bundle[0],'manifest_raw':self._bundle[1],'manifest_pin':copy.deepcopy(self._bundle[2]),
                'native_authorized':False,'atomic_reservation':False,'capacity_pass':False,'lease_completed':False,
                'parent_ack_authorized':False,'execution_authenticated':False}
        except BaseException as error:self._failed(error)

    def readback(self, *, archive_raw, manifest_raw, manifest_pin):
        if self._failure is not None:raise self._failure
        held={'archive_raw':archive_raw,'manifest_raw':manifest_raw,'manifest_pin':manifest_pin}
        self.incoming.append(held);self._incoming+=((held,archive_raw,manifest_raw,manifest_pin),)
        try:
            self._clock();view=self.bundle()
            v.require(type(archive_raw) is bytes and type(manifest_raw) is bytes and
                archive_raw==view['archive_raw'] and manifest_raw==view['manifest_raw'] and
                manifest_pin==view['manifest_pin'],'partition archive external full raw/manifest pin')
            evidence._raw(manifest_raw,manifest_pin,'partition archive original manifest readback')
            manifest=v.strict_json(manifest_raw)
            evidence._raw(archive_raw,manifest['archive_pin'],'partition archive full original raw pin')
            offset=0
            for row,original in zip(manifest['packets'],self._ledger):
                v.require(row['offset']==offset and row['lease']==original[0]['lease'] and
                    archive_raw[offset:offset+row['growth_bytes']]==b''.join(original[4]),
                    'partition archive ordered full packet coverage')
                offset+=row['growth_bytes']
            v.require(offset==len(archive_raw),'partition archive no trailing or partial prefix')
            self._clock();return tuple(original[5] for original in self._ledger)
        except BaseException as error:self._failed(error)

    def execute(self):
        if self._failure is not None:raise self._failure
        raise ValueError('partition archive native/publication admission not prepared')


class ArchiveAppendAdmission:
    """Opt-in frame growth and future control snapshot gate, not atomic reservation.

    Original recovery raw, including partial-archive.bin, stays in the measured
    root. Its raw inventory cap never supplies this new archive frame's bytes.
    Every control publisher must participate before this can authorize native.
    """
    CONTROL_NAMES = tuple(name+suffix for name in (
        'request.json','binding.json','stop.json','worker-inventory.json',
        'git-manifest.json','git-proof.json','ack.json') for suffix in ('','.pending'))
    BYTE_LIMIT, ENTRY_LIMIT, RESERVE = 1024**2, 32, 128*1024

    @classmethod
    def validate_controls(cls, value):
        v.require(type(value) is dict and set(value)==set(cls.CONTROL_NAMES) and
            all(type(n) is int and 0<n<=proof.channel.MAX_CONTROL for n in value.values()),
            'archive append all completed and pending control maxima')
        return value

    def __init__(self, *, root, root_identity, revision, inventory_pin, control_limits, checkpoint):
        self.original_root, self.original_identity, self.original_controls = root, root_identity, control_limits
        self.original_inventory_pin, self.checkpoint = inventory_pin, checkpoint
        self.writer = self.rejected_writer = self.pending = self.error = None
        self.completed = []
        self.root, self.identity = Path(root), copy.deepcopy(root_identity)
        self.revision, self.inventory_pin = revision, copy.deepcopy(inventory_pin)
        self.control_limits = copy.deepcopy(control_limits)
        v.require(self.root.is_absolute() and self.root == self.root.resolve() and
            type(self.identity) is tuple and len(self.identity)==2 and
            all(type(n) is int and n>=0 for n in self.identity) and callable(checkpoint),
            'archive append held root identity and shared checkpoint')
        evidence._digest(revision,40); evidence._pin(self.inventory_pin)
        self.validate_controls(self.control_limits)
        self.plan_raw=self._plan()

    def _plan(self):
        return io.json_bytes({'root':str(self.root),'root_identity':list(self.identity),
            'revision':self.revision,'inventory_pin':self.inventory_pin,'control_limits':self.control_limits})

    def _bound(self):
        writer=self.writer
        v.require(self._plan()==self.plan_raw and writer.checkpoint is self.checkpoint and
            writer.verifier.inventory_pin==self.inventory_pin and
            writer.verifier.endpoint.request['revision']==self.revision and
            Path(writer.verifier.endpoint.request['budget_root'])==self.root and writer.path.parent==self.root,
            'archive append held plan or original binding changed')
        if self.pending is not None:
            v.require(writer.raw is self.pending['before_raw'] and
                self.pending['lease']==len(self.completed)==len(writer.rows),
                'archive append original bytes or sequence changed')

    def _failed(self, failure):
        if self.error is None:self.error=failure
        raise self.error

    def bind(self, writer):
        if self.error is not None:raise self.error
        try:
            if self.writer is not None:
                self.rejected_writer=writer
                v.require(False,'archive append cannot rebind its original writer')
            self.writer=writer  # Before caller clock, root or verifier IO.
            v.require(type(writer) is WorkerGitArchive and writer.checkpoint is self.checkpoint and
                writer.verifier.inventory_pin==self.inventory_pin and
                writer.verifier.endpoint.request['revision']==self.revision and
                Path(writer.verifier.endpoint.request['budget_root'])==self.root and
                writer.path.parent==self.root, 'archive append exact inventory/revision/root/writer')
            self.checkpoint(); self._bound(); writer.verifier._live()
            info=paths.regular_path(self.root,directory=True).lstat()
            v.require((info.st_dev,info.st_ino)==self.identity,'archive append original root changed')
        except BaseException as failure:self._failed(failure)

    def _remaining(self, growth, stage):
        self.checkpoint(); self._bound(); self.writer.verifier._live()
        storage=getattr(self.writer,'original_publication_storage',None)
        if storage is not None:
            if getattr(self,'original_publication_storage',None) is not storage:
                storage._failed(ValueError('archive original publication storage cannot be hidden'))
            storage.view('archive_'+stage)
            v.require(len(self.writer.raw)+growth<=storage.allocation['archive_bytes'],
                'publication storage independent archive bound')
        from . import anomaly_v03_preformal_generated_chain_budget as monitor
        snapshot=monitor._directory_snapshot(self.root,self.ENTRY_LIMIT,2,self.identity)
        held={'snapshot':snapshot,'controls':{}}
        self.pending[stage]=held  # Retain observations before subsequent IO.
        # Do not subtract a later per-control stat from an earlier root scan.
        # A concurrent publisher could otherwise shrink the purported future
        # reservation without its new bytes/entry appearing in the snapshot.
        # Count all slots again until every writer joins an atomic protocol.
        future_bytes=sum(self.control_limits.values())
        future_entries=len(self.control_limits)
        for name,maximum in self.control_limits.items():
            path=self.writer.verifier.endpoint.root/name
            paths.regular_path(path,missing=True)
            info=path.lstat() if path.exists() else None
            held['controls'][name]=None if info is None else {'bytes':info.st_size,'identity':(info.st_dev,info.st_ino)}
            size=0 if info is None else info.st_size
            v.require(size<=maximum,'archive append retained control exceeds held maximum')
        held.update(future_bytes=future_bytes,future_entries=future_entries,growth_bytes=growth)
        v.require(snapshot['directory_bytes']+future_bytes+growth+self.RESERVE<=self.BYTE_LIMIT and
            snapshot['directory_entries']+future_entries+2<=self.ENTRY_LIMIT,
            'archive append frame and future controls exceed original outer remaining budget')

    def reserve(self, writer, lease, frame):
        if self.error is not None:raise self.error
        try:
            v.require(writer is self.writer and self.pending is None and
                type(lease) is int and lease==len(self.completed)==len(writer.rows) and
                type(frame) is bytes and writer.pending['frame'] is frame,
                'archive append original ordered frame')
            self.pending={'lease':lease,'frame':frame,'before_raw':writer.raw}
            v.require(frame[:4]==MAGIC and len(frame)>=8 and
                int.from_bytes(frame[4:8],'big')==len(frame)-8 and len(frame)<=MAX_RECORD+8 and
                len(writer.raw)+len(frame)<=MAX_BYTES,'archive append unchanged frame and archive caps')
            self._remaining(len(frame),'before')
            v.require(observed._file(writer.path,MAX_BYTES)==writer.raw,'archive append original bytes changed')
        except BaseException as failure:self._failed(failure)

    def complete(self, writer):
        if self.error is not None:raise self.error
        try:
            v.require(writer is self.writer and self.pending is not None and
                self.pending['lease']==len(self.completed)==len(writer.rows),
                'archive append original pending completion')
            pending=self.pending
            raw=observed._file(writer.path,MAX_BYTES)
            pending['readback_raw']=raw
            v.require(raw==pending['before_raw']+pending['frame'],'archive append exact added frame readback')
            self._remaining(0,'after')
            row={'lease':pending['lease'],'before_pin':observed._pin(pending['before_raw']),
                'frame_pin':observed._pin(pending['frame']),'archive_pin':observed._pin(raw),
                'atomic_reservation':False,'lease_completed':False,'parent_ack_authorized':False,
                'execution_authenticated':False}
            self.completed.append(row); self.pending=None
        except BaseException as failure:self._failed(failure)


def checked_append_plan(entry, *, request, request_pin, inventory_pin, root_identity):
    """Only bind metadata to original caller pins; never authorize native work."""
    v.require(type(entry) is dict and set(entry)=={'value','pin'},'archive append exact pinned context')
    value=entry['value']; raw=io.json_bytes(value)
    v.require(len(raw)<=proof.channel.MAX_CONTROL,'archive append context byte bound')
    evidence._raw(raw,entry['pin'],'archive append held context pin')
    v.require(type(value) is dict and set(value)=={'format','revision','request_pin','inventory_pin',
        'budget_root','budget_root_identity','control_limits','formal_permission'} and
        value['format']==APPEND_PLAN_FORMAT and value['formal_permission'] is False and
        value['revision']==request['revision'] and value['request_pin']==request_pin and
        value['inventory_pin']==inventory_pin and value['budget_root']==request['budget_root'] and
        value['budget_root_identity']==list(root_identity), 'archive append original request/inventory/root link')
    ArchiveAppendAdmission.validate_controls(value['control_limits'])
    return copy.deepcopy(value['control_limits'])


class ControlPublicationAdmission:
    """Retained named control IO for an existing endpoint, not a shared lock.

    Request bootstrap and issuing this gate to all callers remain separate.
    Python FileIO.close evidence never substitutes for native owner recovery.
    """
    def __init__(self, *, endpoint, inventory_pin, root_identity, control_limits, checkpoint, owner):
        self.original_endpoint = self.endpoint = endpoint
        self.original_owner = self.owner = owner
        self.original_checkpoint = self.checkpoint = checkpoint
        self.original_identity, self.original_controls = root_identity, control_limits
        self.original_inventory_pin = inventory_pin
        self.pending = self.error = None
        self.completed = {}
        try:
            self.identity, self.control_limits = copy.deepcopy(root_identity), copy.deepcopy(control_limits)
            self.inventory_pin = copy.deepcopy(inventory_pin)
            v.require(isinstance(endpoint,proof.channel._Channel) and hasattr(owner,'__dict__') and callable(checkpoint),
                      'control original endpoint, retaining Python owner and checkpoint')
            self.previous_publication_owner=getattr(owner,'control_publication_owner',None)
            if self.previous_publication_owner is not None:
                self.previous_publication_owner.rejected_publication=self
                v.require(False,'control retaining owner cannot replace its original publication gate')
            owner.control_publication_owner=self  # Before checkpoint/file IO; do not replace a prior owner.
            self.request, self.request_pin = copy.deepcopy(endpoint.request), copy.deepcopy(endpoint.request_pin)
            self.root, self.channel_root = Path(self.request['budget_root']), endpoint.root
            v.require(type(self.identity) is tuple and len(self.identity)==2 and
                all(type(n) is int and n>=0 for n in self.identity) and self.identity[1]>0,
                'control original outer identity')
            evidence._pin(self.inventory_pin)
            ArchiveAppendAdmission.validate_controls(self.control_limits)
            self.plan_raw = self._plan()
        except BaseException as error:self._failed(error)

    def _plan(self):
        return io.json_bytes({'request_pin':self.request_pin,'inventory_pin':self.inventory_pin,
            'root':str(self.root),'channel_root':str(self.channel_root),'root_identity':list(self.identity),
            'control_limits':self.control_limits})

    def _failed(self, error):
        if self.error is None:self.error=error
        self.error.control_publication_owner=self  # Retain raw/streams even if the caller propagates this error.
        try:
            storage=getattr(self.owner,'original_publication_storage',None)
            if type(storage) is PublicationStorageAdmission:
                if storage.original_error is None:storage.original_error=self.error
                storage.error=storage.original_error
                self.error.publication_storage=storage  # Same original error; no recursive retry/cleanup.
        except BaseException as retention_error:self.error.publication_storage_retention_error=retention_error
        prior=getattr(self,'previous_publication_owner',None)
        if type(prior) is ControlPublicationAdmission and prior.error is None:
            prior.error=self.error  # A rejected rebind cannot leave the original publication owner armed.
        raise self.error

    def _view(self, stage):
        self.checkpoint()
        v.require(self._plan()==self.plan_raw and self.endpoint is self.original_endpoint and
            self.checkpoint is self.original_checkpoint and self.owner is self.original_owner and
            self.owner.control_publication_owner is self and self.endpoint.request==self.request and
            self.endpoint.request_pin==self.request_pin and self.endpoint.root==self.channel_root,
            'control held plan or original endpoint changed')
        self.endpoint._live()
        storage=self._storage()
        if storage is not None:storage.view('control_'+stage)
        from . import anomaly_v03_preformal_generated_chain_budget as monitor
        snapshot=monitor._directory_snapshot(self.root,32,2,self.identity)
        held={'snapshot':snapshot,'controls':{}}
        self.pending[stage]=held
        for name,maximum in self.control_limits.items():
            path=self.channel_root/name
            paths.regular_path(path,missing=True)
            info=path.lstat() if path.exists() else None
            held['controls'][name]=None if info is None else {'bytes':info.st_size,
                'identity':(info.st_dev,info.st_ino)}
            v.require(info is None or info.st_size<=maximum,'control retained raw exceeds held maximum')
        # Keep every future slot, including already observed files. No discount
        # based on a later stat from a different publication instant.
        future_bytes, future_entries=sum(self.control_limits.values()),len(self.control_limits)
        held.update(future_bytes=future_bytes,future_entries=future_entries)
        v.require(snapshot['directory_bytes']+future_bytes+128*1024<=1024**2 and
            snapshot['directory_entries']+future_entries+2<=32,
            'control future frames exceed original outer byte/entry reserve')

    def _readback(self, path, stage):
        raw=observed._file(path,proof.channel.MAX_CONTROL)
        self.pending[stage]=raw
        evidence._raw(raw,self.pending['pin'],'control original raw readback')
        v.require(raw==self.pending['raw'],'control exact raw readback')
        return raw

    def publish(self, path, value):
        if self.error is not None:raise self.error
        try:
            v.require(self.pending is None,'control original publication already pending')
            self.pending={'path':path,'value':value,'owner':self.owner,'stream':None,'fd':None,
                'raw':None,'write_return':None,'close_return':None,'close_return_observed':False}
            pending=self.pending
            path=Path(path);name=path.name
            v.require(path==self.channel_root/name and name in self.control_limits and
                not name.endswith('.pending') and name not in self.completed,
                'control fixed completed name and exclusive publication')
            raw=io.json_bytes(value);pending['raw']=raw;pending['pin']=observed._pin(raw)
            v.require(type(value) is dict and len(raw)<=self.control_limits[name] and
                len(raw)<=self.control_limits[name+'.pending'] and len(raw)<=proof.channel.MAX_CONTROL,
                'control actual canonical raw within both caller slots')
            if name=='request.json':
                evidence._raw(raw,self.request_pin,'control original request pin')
            elif name=='worker-inventory.json':
                evidence._raw(raw,self.inventory_pin,'control original inventory pin')
            elif name=='git-manifest.json':
                v.require(value.get('inventory_pin')==self.inventory_pin,'control manifest inventory link')
            elif name in ('binding.json','stop.json','ack.json'):
                v.require(value.get('request_pin')==self.request_pin,'control original request link')
            self._view('before')
            staging=path.with_name(name+'.pending');pending['staging']=staging
            paths.regular_path(path,missing=True);paths.regular_path(staging,missing=True)
            v.require(not path.exists() and not staging.exists(),'control no overwrite or staging reuse')
            pending['file_factory']=proof.tree.file_io.FileIO
            stream=pending['stream']=pending['file_factory'](staging,'xb')
            fd=pending['fd']=stream.fileno()
            info=os.fstat(fd);pending['initial_file_identity']=(info.st_dev,info.st_ino)
            v.require(info.st_ino>0 and info.st_size==0 and
                pending['initial_file_identity']==(staging.stat().st_dev,staging.stat().st_ino),
                'control original exclusive empty fd/path')
            pending['write_attempted']=True
            pending['write_return']=stream.write(raw)
            v.require(type(pending['write_return']) is int and pending['write_return']==len(raw),
                      'control exact original write return')
            stream.flush();os.fsync(fd)
            info=os.fstat(fd);pending['written_file_identity']=(info.st_dev,info.st_ino)
            v.require(pending['written_file_identity']==pending['initial_file_identity'] and info.st_size==len(raw),
                      'control original fd/count after sync')
            self._readback(staging,'staging_raw')
            self._view('written')
            pending['close_attempted']=True
            pending['close_return']=stream.close()
            pending['close_return_observed']=True
            v.require(pending['close_return'] is None and stream.closed is True and stream.closefd is True,
                      'control observed Python owned fd close return')
            self._readback(staging,'closed_raw')
            pending['rename_attempted']=True
            pending['rename_return']=io._rename_no_replace(staging,path)
            v.require(pending['rename_return'] is None,'control observed no-replace publication return')
            self._readback(path,'published_raw')
            info=path.lstat();pending['published_file_identity']=(info.st_dev,info.st_ino)
            v.require(pending['published_file_identity']==pending['initial_file_identity'],
                      'control original file identity after publication')
            self._view('after')
            row={'pin':copy.deepcopy(pending['pin']),'file_identity':pending['published_file_identity'],
                'python_close_return':pending['close_return'],'atomic_reservation':False,
                'native_owner_recovered':False,'parent_ack_authorized':False,'execution_authenticated':False}
            self.completed[name]={'observation':row,'original':pending}
            self.pending=None
            return copy.deepcopy(row['pin'])
        except BaseException as error:self._failed(error)

    def verify_publications(self, names, *, cached=False, extended=False):
        """One final original close/raw check; no stream/native close or retry."""
        if self.error is not None:raise self.error
        try:
            v.require(type(cached) is bool and type(extended) is bool and (not extended or cached) and self.pending is None and
                (hasattr(self,'verification') if cached else not hasattr(self,'verification')),
                'control original completed verification or explicit cached readback')
            self.pending={'verification_names':names,'original_completed':self.completed,'raw':{},
                          'original_verification':getattr(self,'verification',None)}
            if cached:
                initial=self.verification['verification_names']
                v.require(type(names) is tuple and (names[:len(initial)]==initial if extended else initial==names),
                          'control cached original completed names or explicit extension')
            v.require(type(names) is tuple and set(names)==set(self.completed) and len(names)==len(set(names)),
                      'control final exact completed names')
            self._view('verify_before')
            for name in names:
                row=self.completed[name];original=row['original'];observation=row['observation']
                v.require(original['owner'] is self.owner and original['close_return_observed'] is True and
                    original['close_return'] is None and original['stream'].closed is True and
                    original['stream'].closefd is True and original['rename_return'] is None and
                    original['published_file_identity']==original['initial_file_identity']==observation['file_identity'],
                    'control original owned fd close and publication returns')
                path=self.channel_root/name;raw=observed._file(path,proof.channel.MAX_CONTROL)
                self.pending['raw'][name]=raw
                evidence._raw(raw,observation['pin'],'control final original published raw')
                info=path.lstat()
                v.require(raw==original['raw']==original['published_raw'] and
                    (info.st_dev,info.st_ino)==original['published_file_identity'],
                    'control final raw or original file identity changed')
            self._view('verify_after')
            if cached:self.cached_verification=self.pending
            else:self.verification=self.pending
            self.pending=None
            return {name:copy.deepcopy(self.completed[name]['observation']['pin']) for name in names}
        except BaseException as error:self._failed(error)

    def capture_pending(self):
        """A local witness never hides pending IO from the original keeper."""
        storage=self._storage()
        if storage is not None and storage.unresolved():return True
        carrier=getattr(self,'original_publication_carrier',None)
        if carrier is not None:
            if carrier.unresolved():return True
        original=getattr(self,'original_child_publication_capture',None)
        sidecar=getattr(self.owner,'child_publication_capture',None)
        if original is None and sidecar is None:return False
        try:
            if original is not sidecar:
                self.rejected_child_capture=(original,sidecar)
            if type(original) is ChildPublicationCapture and original.error is not None:
                if self.error is None:self.error=original.error
                return True  # Clearing metadata cannot discard the original capture failure.
            v.require(type(original) is ChildPublicationCapture and original is sidecar and
                original.gate is self and original.actor is self.owner,
                'control original local child capture owner')
            if original.error is not None or original.pending is not None:return True
            original._check()
            return False
        except BaseException as error:
            if type(original) is ChildPublicationCapture:original._failed(error)
            self._failed(error)

    def arm_publication_carrier(self, creator, *, frame_limit):
        return PublicationCarrier(creator=creator,owner=self,checkpoint=self.checkpoint,
            frame_limit=frame_limit,sending=True,
            storage_admission=self._storage())

    def _storage(self):
        original=getattr(self.owner,'original_publication_storage',None)
        gate=getattr(self,'original_publication_storage',None)
        sidecar=getattr(self,'publication_storage',None)
        if original is None and gate is None and sidecar is None:return None
        self.rejected_storage_binding=(original,gate,sidecar)
        try:
            v.require(type(original) is PublicationStorageAdmission and original is gate is sidecar and
                original.gate is self and original.owner is self.owner,'control original storage cannot be hidden')
            return original
        except BaseException as error:
            if type(original) is PublicationStorageAdmission:original._failed(error)
            self._failed(error)


class ChildPublicationCapture:
    """Keep local FileIO returns/raw in memory; no parent transport or ack."""
    NAMES=('git-manifest.json','git-proof.json','ack.json')

    def __init__(self, *, gate, actor):
        self.gate,self.actor=gate,actor
        self.error=self.completion=self.rejected_capture=None
        self.pending={'gate':gate,'actor':actor}
        self.original_inputs=(gate,actor,self.pending)  # Before validation, copy or clock/readback IO.
        try:
            self.pending['reader_publication']=getattr(actor,'reader_publication',None)
            self.pending['endpoint']=getattr(gate,'endpoint',None)
            self.pending['completed']=getattr(gate,'completed',None)
            from .anomaly_v03_preformal_worker_git_actor import WorkerGitActor
            v.require(type(gate) is ControlPublicationAdmission and type(actor) is WorkerGitActor,
                      'capture original child gate and actor')
            prior=getattr(gate,'original_child_publication_capture',None)
            self.previous_capture=prior
            if prior is not None:
                prior.rejected_capture=self
                prior._failed(ValueError('capture original owner cannot be replaced'))
            gate.original_child_publication_capture=self
            previous=getattr(actor,'child_publication_capture',None)
            self.previous_actor_capture=previous
            actor.child_publication_capture=self  # Keep even rejected inputs before validation/copy.
            v.require(previous is None and gate.owner is actor and actor.control_publication is gate and
                actor.control_publication_owner is gate and gate.endpoint is actor.child and
                isinstance(actor.child,proof.channel.ChildChannel) and gate.checkpoint is actor.checkpoint and
                gate.error is None and gate.pending is None and not gate.completed and
                not hasattr(gate,'verification'),'capture same original unpublished child owner')
            self.endpoint=actor.child
            self.publication=self.pending['reader_publication']
            self.completed=self.pending['completed']
            v.require(type(self.publication) is dict,'capture original reader publication input')
            self.pending['core_context']=self._context()
            self.core_raw=io.json_bytes(self.pending['core_context'])
            v.require(len(self.core_raw)<=proof.channel.MAX_CONTROL,'capture bounded original context')
        except BaseException as error:self._failed(error)

    def _failed(self, error):
        if self.error is None:self.error=getattr(self.gate,'error',None) or error
        self.error.child_publication_capture=self
        if type(self.gate) is ControlPublicationAdmission:self.gate._failed(self.error)
        raise self.error

    def _context(self):
        gate,child=self.gate,self.endpoint
        return {'request_pin':gate.request_pin,'inventory_pin':gate.inventory_pin,
            'root_identity':list(gate.identity),'clock':child.request['clock'],
            'root':str(child.root),'revision':child.request['revision'],'worker_identity':child.identity}

    def _rows(self):
        gate=self.gate;held=self.state
        v.require(gate.original_child_publication_capture is self and self.actor.child_publication_capture is self and
            gate.owner is self.actor and gate.original_owner is self.actor and gate.endpoint is self.endpoint and
            gate.original_endpoint is self.endpoint and gate.checkpoint is gate.original_checkpoint is
                self.actor.checkpoint and gate._plan()==gate.plan_raw and
            self.endpoint.request==gate.request and self.endpoint.request_pin==gate.request_pin and
            self.actor.control_publication is gate and
            self.actor.control_publication_owner is gate and self.actor.reader_publication is self.publication and
            gate.completed is self.completed and gate.verification is held['verification'] and
            held['verification']['verification_names']==self.NAMES and set(self.completed)==set(self.NAMES) and
            gate.inventory_pin==self.actor.inventory_pin and io.json_bytes(self._context())==self.core_raw,
            'capture fixed original owner, context and verification')
        rows={};total=0
        for name in self.NAMES:
            row=self.completed[name];original=row['original'];observation=row['observation']
            v.require(row is held['rows'][name] and original is held['originals'][name] and
                original['owner'] is self.actor and original['stream'] is held['streams'][name] and
                original['close_return_observed'] is True and original['close_return'] is None and
                'rename_return' in original and original['rename_return'] is None and
                original['stream'].closed is True and original['stream'].closefd is True and
                type(original['fd']) is int and original['fd']>=0 and
                original['published_file_identity']==original['written_file_identity']==
                    original['initial_file_identity']==observation['file_identity'],
                'capture original Python fd close and rename returns')
            raw=held['raw'][name]
            v.require(type(raw) is bytes and len(raw)<=proof.channel.MAX_CONTROL and
                raw==original['raw']==original['published_raw']==held['verification']['raw'][name] and
                original['write_return']==len(raw),'capture original verified raw and write count')
            evidence._raw(raw,observation['pin'],'capture original raw pin')
            total+=len(raw)
            rows[name]={'pin':observation['pin'],'fd':original['fd'],
                'file_identity':list(observation['file_identity']),'python_close_return':None,'rename_return':None}
        v.require(total<=3*proof.channel.MAX_CONTROL and held['returned_pins']==
            {name:row['pin'] for name,row in rows.items()},'capture bounded separate raw and original verification return')
        ack=v.strict_json(held['raw']['ack.json'])
        evidence._keys(ack,'format request_pin binding_pin worker_identity no_new_jobs jobs_finished proof','capture ack fields')
        v.require(ack['format']==proof.channel.FORMAT+'-ack' and ack['request_pin']==self.gate.request_pin and
            ack['worker_identity']==self.endpoint.identity and ack['no_new_jobs'] is True and
            type(ack['jobs_finished']) is int and ack['jobs_finished']==self.endpoint.finished>0 and
            ack['proof']=={'path':str(self.endpoint.root/'git-proof.json'),'pin':rows['git-proof.json']['pin']} and
            self.publication['ack_pin']==rows['ack.json']['pin'],'capture original bound ack context')
        evidence._pin(ack['binding_pin'])
        return {'format':'anomaly-v03-child-publication-local-capture-v1','context':self._context(),
            'binding_pin':ack['binding_pin'],'publications':rows,'raw_bytes':total,
            'parent_ack_authorized':False,'execution_authenticated':False,'atomic_reservation':False}

    def _check(self):
        v.require(self.completion is not None and self.error is None and self.pending is None,
                  'capture completed original local observation')
        raw=io.json_bytes(self._rows())
        v.require(raw==self.payload_raw==self.completion['payload_raw'] and
            self.completion['original_state'] is self.state and self.completion['gate'] is self.gate and
            all(self.completion[key] is False for key in
                ('parent_ack_authorized','execution_authenticated','atomic_reservation')),
            'capture fixed local payload and retaining owner')
        evidence._raw(raw,self.completion['payload_pin'],'capture original local envelope pin')

    def seal(self, returned_pins):
        if self.error is not None:raise self.error
        if self.completion is not None:
            self.rejected_cached_return=returned_pins  # Preserve before memory-only validation; no IO replay.
            try:
                v.require(returned_pins==self.state['returned_pins'],'capture original cached return')
                self._check();return self.completion
            except BaseException as error:self._failed(error)
        self.original_seal_return=returned_pins  # Original return, even if the pending metadata is damaged.
        try:
            v.require(type(self.pending) is dict,'capture original pending state')
            self.pending['returned_pins']=returned_pins  # Before getter/validation/clock IO.
            gate=self.gate;held=self.state=self.pending
            held['gate_pending']=gate.pending
            held['verification']=getattr(gate,'verification',None)
            held['rows']={name:self.completed.get(name) for name in self.NAMES}
            held['originals']={name:row['original'] for name,row in held['rows'].items()}
            held['streams']={name:row['stream'] for name,row in held['originals'].items()}
            held['raw']={name:row['published_raw'] for name,row in held['originals'].items()}
            v.require(gate.error is None and gate.pending is None,'capture no unresolved control IO')
            gate.pending={'local_child_capture':self,'original_state':held}
            payload=self._rows();held['payload']=payload
            raw=held['payload_raw']=io.json_bytes(payload)
            v.require(len(raw)<=proof.channel.MAX_CONTROL,'capture separate bounded envelope without raw embedding')
            gate._view('capture')  # Original shared clock/root; every owner/raw is already held.
            v.require(io.json_bytes(self._rows())==raw,'capture callback cannot alter original observations')
            self.payload_raw=raw
            self.completion={'gate':gate,'original_state':held,'payload_raw':raw,'payload_pin':observed._pin(raw),
                'parent_ack_authorized':False,'execution_authenticated':False,'atomic_reservation':False}
            self.pending=None;gate.pending=None
            return self.completion
        except BaseException as error:self._failed(error)


STORAGE_CONTEXT_FORMAT = 'anomaly-v03-publication-storage-context-v1'


def checked_storage_allocation(entry):
    v.require(type(entry) is dict and set(entry)=={'value','pin'},'storage exact caller allocation pin')
    raw=io.json_bytes(entry['value'])
    evidence._raw(raw,entry['pin'],'storage caller allocation original pin')
    PublicationStorageAdmission.validate_allocation(entry['value'])
    return entry['value']


def checked_storage_plan(entry, *, request, request_pin, inventory_pin, root_identity):
    v.require(type(entry) is dict and set(entry)=={'value','pin'},'storage exact linked context pin')
    value=entry['value'];raw=io.json_bytes(value)
    v.require(len(raw)<=proof.channel.MAX_CONTROL,'storage linked context bounded')
    evidence._raw(raw,entry['pin'],'storage linked context original pin')
    fields={'format','revision','request_pin','inventory_pin','budget_root','budget_root_identity',
        'clock','allocation','formal_permission'}
    v.require(type(value) is dict and set(value)==fields and value['format']==STORAGE_CONTEXT_FORMAT and
        value['formal_permission'] is False and value['revision']==request['revision'] and
        value['request_pin']==request_pin and value['inventory_pin']==inventory_pin and
        value['budget_root']==request['budget_root'] and value['budget_root_identity']==list(root_identity) and
        value['clock']==request['clock'],'storage exact request/inventory/root/clock context')
    return checked_storage_allocation(value['allocation'])


class PublicationStoragePreparation:
    """Retain the caller allocation before request/inventory publication exists.

    This conservative snapshot gate issues no request, inventory or native
    permission. Those original values are linked only after their real returns.
    """
    def __init__(self, *, root, revision, budget, allocation, controls, raw_limits, source_pins, names,
                 checkpoint, owner, policy, profile_pin, repository):
        self.original_inputs=(root,revision,budget,allocation,controls,raw_limits,source_pins,names,checkpoint,owner,
            policy,profile_pin,repository)
        self.owner,self.budget,self.checkpoint=owner,budget,checkpoint
        self.error=self.original_error=self.bound_storage=self.pending=None
        self.endpoint=self.inventory_raw=self.inventory_pin=None
        try:
            self.previous=getattr(owner,'original_storage_preparation',None)
            if self.previous is not None:
                self.previous.rejected_preparation=self
                self.previous._failed(ValueError('storage original preparation cannot be replaced'))
            owner.original_storage_preparation=owner.storage_preparation=self  # Before copy, getters or IO.
            self.pending={'inputs':self.original_inputs}
            self.allocation_entry=copy.deepcopy(allocation);checked_storage_allocation(self.allocation_entry)
            self.allocation=self.allocation_entry['value']
            self.controls=copy.deepcopy(controls);ArchiveAppendAdmission.validate_controls(self.controls)
            self.raw_limits=copy.deepcopy(raw_limits);self.source_pins=copy.deepcopy(source_pins)
            self.names=copy.deepcopy(names);self.revision=copy.deepcopy(revision)
            self.policy=copy.deepcopy(policy);self.profile_pin=copy.deepcopy(profile_pin)
            self.repository=copy.deepcopy(repository)
            evidence._pin(self.profile_pin)
            v.require(type(self.policy) is dict and set(self.policy)=={'path','expected_pin'},'storage original private policy pin')
            evidence._pin(self.policy['expected_pin'])
            evidence._digest(self.revision,40)
            v.require(type(self.names) is tuple and len(set(self.names))==len(self.names) and
                type(self.source_pins) is dict and set(self.source_pins)==set(self.names) and
                type(self.raw_limits) is dict and set(self.raw_limits)=={'head','status','source_blob'},
                'storage preparation exact caller source/call allocation')
            for pin in self.source_pins.values():evidence._pin(pin)
            for operation,raw in self.raw_limits.items():
                maximum={'stdout.bin':proof.tree.direct.MAX_OUTPUT[operation],'stderr.bin':proof.tree.direct.MAX_STDERR,
                    'receipt.json':proof.tree.direct.MAX_RECEIPT,'partial-archive.bin':MAX_BYTES}
                v.require(type(raw) is dict and {'stdout.bin','stderr.bin','receipt.json'}<=set(raw)<=set(maximum) and
                    all(type(n) is int and 0<n<=maximum[name] for name,n in raw.items()),
                    'storage preparation independent original raw maxima')
            self.raw_bytes=max(sum(row.values()) for row in self.raw_limits.values())
            self.raw_entries=max(len(row) for row in self.raw_limits.values())
            v.require(callable(checkpoint) and budget is not None,'storage original shared budget/checkpoint')
            self.roots=copy.deepcopy(budget.roots)
            self.pending['clock_observation']=clock_info=proof.channel.time.get_clock_info('monotonic')
            self.clock={'started_at':budget.started_at,'wall_seconds':budget.limits['wall_seconds'],
                'implementation':clock_info.implementation}
            self.root=Path(self.roots['outer']);self.channel_root=Path(root).absolute()
            v.require(self.channel_root.parent==self.root,'storage original channel under shared outer')
            self.plan_raw=self._plan();v.require(len(self.plan_raw)<=proof.channel.MAX_CONTROL,'storage preparation bound')
            self.plan_pin=observed._pin(self.plan_raw)
            self.view('before_request')
        except BaseException as error:self._failed(error)

    def _plan(self):
        return io.json_bytes({'allocation':self.allocation_entry,'controls':self.controls,'raw_limits':self.raw_limits,
            'source_pins':self.source_pins,'names':list(self.names),'revision':self.revision,
            'root':str(self.root),'channel_root':str(self.channel_root),'clock':self.clock,'policy':self.policy,
            'profile_pin':self.profile_pin,'repository':str(self.repository)})

    def _failed(self,error):
        if self.original_error is None:self.original_error=error
        self.error=self.original_error;self.error.storage_preparation=self
        self.error.reader_git_parent=self.owner
        if getattr(self.owner,'error',None) is None:self.owner.error=self.error
        raise self.error

    def _fixed(self):
        if self.original_error is not None:raise self.original_error
        v.require(self.owner is self.original_inputs[9] and self.checkpoint is self.original_inputs[8] and
            self.budget is self.original_inputs[2] and self.owner.original_storage_preparation is self.owner.storage_preparation is self
            and self.budget.roots==self.roots and self.budget.started_at==self.clock['started_at'] and
            self.budget.limits['wall_seconds']==self.clock['wall_seconds'] and self._plan()==self.plan_raw,
            'storage original preparation sidecar/clock/plan')
        evidence._raw(self.plan_raw,self.plan_pin,'storage preparation original plan pin')
        if self.bound_storage is not None:
            v.require(self.owner.original_publication_storage is self.bound_storage and
                self.bound_storage.endpoint is self.endpoint and self.bound_storage.inventory_raw is self.inventory_raw and
                self.bound_storage.inventory_pin==self.inventory_pin and self.bound_storage.allocation==self.allocation,
                'storage preparation original returned request/inventory/owner')

    def unresolved(self):
        if self.original_error is not None:self.error=self.original_error;return True
        try:self._fixed();return self.pending is not None
        except BaseException as error:self._failed(error)

    def view(self,stage):
        try:
            self.pending={'stage':stage,'inputs':self.original_inputs}
            self.checkpoint();self._fixed()
            stat=paths.regular_path(self.root,directory=True).lstat()
            self.pending['root_stat']=stat  # Original return before the snapshot/checkpoint.
            identity=(stat.st_dev,stat.st_ino)
            prior=getattr(self,'identity',None)
            v.require(prior is None or prior==identity,'storage preparation original root identity')
            self.identity=identity
            from . import anomaly_v03_preformal_generated_chain_budget as monitor
            self.pending['snapshot']=snapshot=monitor._directory_snapshot(self.root,32,2,identity)
            future=sum(self.controls.values())+self.raw_bytes+self.allocation['archive_bytes']+\
                self.allocation['carrier_failure_bytes']+sum(self.allocation['parent_raw_limits'].values())
            entries=len(self.controls)+self.raw_entries+2+len(self.allocation['parent_raw_limits'])+2
            # Include the not-yet-created channel; never discount observed controls.
            channel_growth=0 if self.channel_root.exists() else 1
            self.pending['remaining_bytes']=1024**2-128*1024-snapshot['directory_bytes']-future
            self.pending['remaining_entries']=32-2-snapshot['directory_entries']-entries-channel_growth
            v.require(self.pending['remaining_bytes']>=0 and self.pending['remaining_entries']>=0,
                'storage before-request future slots exceed original outer reserve')
            self._fixed();self.last_observation=self.pending;self.pending=None
            return self.last_observation
        except BaseException as error:self._failed(error)

    def bind(self,endpoint,inventory_raw,inventory_pin,checkpoint):
        self.rejected_binding=(endpoint,inventory_raw,inventory_pin,checkpoint)  # Before copy/IO.
        try:
            self._fixed();v.require(self.bound_storage is None,'storage preparation binds original inventory once')
            self.endpoint,self.inventory_raw=endpoint,inventory_raw
            self.inventory_pin=copy.deepcopy(inventory_pin)
            v.require(endpoint.root==self.channel_root and endpoint.request['revision']==self.revision and
                endpoint.request['budget_root']==str(self.root) and endpoint.request['clock']==self.clock and
                self.owner.inventory_root_identity==self.identity,'storage preparation observed endpoint/root/clock')
            storage=PublicationStorageAdmission(endpoint=endpoint,inventory_raw=inventory_raw,inventory_pin=inventory_pin,
                root_identity=self.identity,allocation=self.allocation,checkpoint=checkpoint,owner=self.owner)
            self.bound_storage=storage  # Original return before another observation.
            v.require(storage.raw_bytes==self.raw_bytes and storage.raw_entries==self.raw_entries,
                'storage issued inventory uses original call maxima')
            self._fixed();return storage
        except BaseException as error:self._failed(error)


class PublicationStorageAdmission:
    """Coupled conservative snapshot gate, not atomic/global/native admission.

    Caller failure caps, future archive growth and carrier recovery are separate
    quantities. All future controls are counted again to preserve the existing
    refusal at concurrent publication races. Occupied roots may be refused even
    when their current bytes fit. No successful-size-derived failure cap.
    """
    FORMAT='anomaly-v03-publication-storage-allocation-v1'
    PARENT_MAX={'stdout.bin':1024**2,'stderr.bin':64*1024,'receipt.json':32*1024,
                'partial-archive.bin':MAX_BYTES}

    @classmethod
    def validate_allocation(cls,value):
        evidence._keys(value,'format frame_bytes archive_bytes carrier_failure_bytes resident_raw_bytes parent_raw_limits',
            'publication storage closed allocation')
        v.require(value['format']==cls.FORMAT and
            all(type(value[name]) is int for name in ('frame_bytes','archive_bytes','carrier_failure_bytes','resident_raw_bytes')) and
            40<value['frame_bytes']<=proof.channel.MAX_CONTROL and 0<value['archive_bytes']<=MAX_BYTES and
            2*value['frame_bytes']<=value['carrier_failure_bytes']<=2*proof.channel.MAX_CONTROL,
            'publication storage independent positive hard bounds')
        # Byte-buffer bound only: Python objects/runtime/RSS remain unmeasured.
        minimum=128*4096+20*proof.channel.MAX_CONTROL+8*value['frame_bytes']
        v.require(minimum<=value['resident_raw_bytes']<=2*1024**2,'publication storage retained byte buffer bound')
        raw=value['parent_raw_limits']
        v.require(type(raw) is dict and {'stdout.bin','stderr.bin','receipt.json'}<=set(raw)<=set(cls.PARENT_MAX) and
            all(type(n) is int and 0<n<=cls.PARENT_MAX[name] for name,n in raw.items()),
            'publication storage original parent failure maxima')
        v.require(len(io.json_bytes(value))<=proof.channel.MAX_CONTROL,'publication storage allocation byte bound')
        return value

    def __init__(self, *, endpoint, inventory_raw, inventory_pin, root_identity, allocation, checkpoint, owner,
                 issuance_context=None):
        self.original_inputs=(endpoint,inventory_raw,inventory_pin,root_identity,allocation,checkpoint,owner,issuance_context)
        self.endpoint,self.inventory_raw,self.owner,self.checkpoint=endpoint,inventory_raw,owner,checkpoint
        self.error=self.original_error=self.pending=self.last_observation=None
        self.writer=self.rejected_writer=self.sink=self.rejected_sink=None
        self.carriers=[]
        try:
            prior=getattr(owner,'original_publication_storage',None)
            self.previous=prior
            if prior is not None:
                prior.rejected_storage=self;prior._failed(ValueError('publication storage cannot rebind original owner'))
            owner.original_publication_storage=owner.publication_storage=self
            self.allocation=copy.deepcopy(allocation)
            self.identity=copy.deepcopy(root_identity);self.inventory_pin=copy.deepcopy(inventory_pin)
            self.request=copy.deepcopy(endpoint.request);self.request_pin=copy.deepcopy(endpoint.request_pin)
            self.issuance_context=copy.deepcopy(issuance_context)
            self.root=Path(self.request['budget_root']);self.channel_root=endpoint.root
            self.gate=getattr(owner,'control_publication',None) or getattr(owner,'inventory_publication',None)
            self.validate_allocation(self.allocation)
            if issuance_context is not None:
                issued=checked_storage_plan(self.issuance_context,request=self.request,request_pin=self.request_pin,
                    inventory_pin=self.inventory_pin,root_identity=self.identity)
                v.require(issued==self.allocation,'storage original issuance allocation')
                self.issuance_raw=io.json_bytes(self.issuance_context)
            v.require(isinstance(endpoint,proof.channel._Channel) and type(self.gate) is ControlPublicationAdmission and
                self.gate.owner is owner and self.gate.endpoint is endpoint and self.gate.checkpoint is checkpoint and
                self.gate.inventory_pin==self.inventory_pin and self.gate.identity==self.identity,
                'publication storage exact original control owner/context')
            self.gate.original_publication_storage=self.gate.publication_storage=self
            evidence._raw(inventory_raw,self.inventory_pin,'publication storage exact caller inventory raw')
            self.inventory=v.strict_json(inventory_raw)
            self.verifier=proof.ProofVerifier(endpoint=endpoint,inventory_raw=inventory_raw,
                inventory_pin=self.inventory_pin,read_evidence=lambda _:None)
            maxima=[]
            for call in self.inventory['calls']:
                raw=call['raw_inventory']
                maximum={'stdout.bin':proof.tree.direct.MAX_OUTPUT[call['operation']],
                    'stderr.bin':proof.tree.direct.MAX_STDERR,'receipt.json':proof.tree.direct.MAX_RECEIPT,
                    'partial-archive.bin':MAX_BYTES}
                v.require({'stdout.bin','stderr.bin','receipt.json'}<=set(raw)<=set(maximum) and
                    all(type(n) is int and 0<n<=maximum[name] for name,n in raw.items()),
                    'publication storage original call failure inventory')
                maxima.append((sum(raw.values()),len(raw)))
            v.require(maxima,'publication storage nonempty exact inventory')
            self.raw_bytes=max(n for n,_ in maxima);self.raw_entries=max(n for _,n in maxima)
            self.plan_raw=io.json_bytes({'format':self.FORMAT,'request_pin':self.request_pin,
                'inventory_pin':self.inventory_pin,'root':str(self.root),'root_identity':list(self.identity),
                'clock':self.request['clock'],'revision':self.request['revision'],
                'allocation':self.allocation,'control_limits':self.gate.control_limits,
                'raw_bytes':self.raw_bytes,'raw_entries':self.raw_entries})
            v.require(len(self.plan_raw)<=proof.channel.MAX_CONTROL,'publication storage bounded linked plan')
            self.plan_pin=observed._pin(self.plan_raw)
            self.view('arm')
        except BaseException as error:self._failed(error)

    def _failed(self,error):
        if self.original_error is None:self.original_error=error
        self.error=self.original_error;self.error.publication_storage=self
        gate=getattr(self,'gate',None)
        if type(gate) is ControlPublicationAdmission:gate._failed(self.error)
        remember=getattr(self.owner,'_remember_publication',None)
        if callable(remember):remember(self.error)
        raise self.error

    def _fixed(self):
        if self.original_error is not None:raise self.original_error
        if self.gate.error is not None:raise self.gate.error
        preparation=getattr(self.owner,'original_storage_preparation',None)
        if preparation is not None:
            try:preparation._fixed()
            except BaseException as error:preparation._failed(error)
        if self.original_inputs[7] is not None:
            self.rejected_issuance_raw=io.json_bytes(self.original_inputs[7])
            v.require(self.rejected_issuance_raw==self.issuance_raw and
                io.json_bytes(self.issuance_context)==self.issuance_raw,'storage original caller context cannot follow callbacks')
        v.require(self.endpoint is self.original_inputs[0] and self.inventory_raw is self.original_inputs[1] and
            self.checkpoint is self.original_inputs[5] and self.owner is self.original_inputs[6] and
            self.owner.original_publication_storage is self.owner.publication_storage is self and
            self.gate.original_publication_storage is self.gate.publication_storage is self and
            self.gate.owner is self.owner and self.gate.endpoint is self.endpoint and
            self.gate.checkpoint is self.checkpoint and self.gate.inventory_pin==self.inventory_pin and
            self.gate.identity==self.identity and self.endpoint.request==self.request and
            self.endpoint.request_pin==self.request_pin and self.endpoint.root==self.channel_root,
            'publication storage same original sidecar/clock/request/root')
        raw=io.json_bytes({'format':self.FORMAT,'request_pin':self.request_pin,'inventory_pin':self.inventory_pin,
            'root':str(self.root),'root_identity':list(self.identity),'clock':self.request['clock'],
            'revision':self.request['revision'],'allocation':self.allocation,'control_limits':self.gate.control_limits,
            'raw_bytes':self.raw_bytes,'raw_entries':self.raw_entries})
        v.require(raw==self.plan_raw,'publication storage original plan cannot follow callback changes')
        evidence._raw(raw,self.plan_pin,'publication storage original plan pin')
        evidence._raw(self.inventory_raw,self.inventory_pin,'publication storage original inventory pin')
        if self.writer is not None:
            v.require(getattr(self.writer,'original_publication_storage',None) is self and
                self.writer.append_admission.original_publication_storage is self,
                'publication storage original writer and append gate')

    def unresolved(self):
        try:
            if self.original_error is not None:
                self.error=self.original_error
                if self.gate.error is None:self.gate.error=self.error
                return True
            self._fixed();return self.pending is not None
        except BaseException as error:self._failed(error)

    def view(self,stage):
        if self.original_error is not None:raise self.original_error
        try:
            self.pending={'stage':stage,'owner':self.owner,'endpoint':self.endpoint,'inventory_raw':self.inventory_raw}
            self.checkpoint();self._fixed();self.endpoint._live()
            from . import anomaly_v03_preformal_generated_chain_budget as monitor
            held=self.pending
            held['snapshot']=snapshot=monitor._directory_snapshot(self.root,32,2,self.identity)
            held['controls']={}
            for name,maximum in self.gate.control_limits.items():
                path=self.channel_root/name;paths.regular_path(path,missing=True)
                info=path.lstat() if path.exists() else None
                held['controls'][name]=None if info is None else {'bytes':info.st_size,'identity':(info.st_dev,info.st_ino)}
                v.require(info is None or info.st_size<=maximum,'publication storage original control maximum')
            archive_path=self.root/'worker-git.bin';paths.regular_path(archive_path,missing=True)
            held['archive_bytes']=archive_path.stat().st_size if archive_path.exists() else 0
            v.require(held['archive_bytes']<=self.allocation['archive_bytes'],'publication storage existing archive maximum')
            future=sum(self.gate.control_limits.values())+self.raw_bytes+self.allocation['archive_bytes']+\
                self.allocation['carrier_failure_bytes']+sum(self.allocation['parent_raw_limits'].values())
            future_entries=len(self.gate.control_limits)+self.raw_entries+1+1+\
                len(self.allocation['parent_raw_limits'])+2
            held.update(future_bytes=future,future_entries=future_entries,
                remaining_bytes=ArchiveAppendAdmission.BYTE_LIMIT-ArchiveAppendAdmission.RESERVE-snapshot['directory_bytes']-future,
                remaining_entries=32-2-snapshot['directory_entries']-future_entries,
                resident_raw_bytes=self.allocation['resident_raw_bytes'],atomic_reservation=False,
                capacity_pass=False,private_memory_measured=False,all_publishers_registered=False,
                native_launch_authorized=False,parent_ack_authorized=False,execution_authenticated=False)
            v.require(held['remaining_bytes']>=0 and held['remaining_entries']>=0,
                'publication storage all future quantities exceed original outer remaining')
            self._fixed();self.last_observation=held;self.pending=None;return held
        except BaseException as error:self._failed(error)

    def native_launch_preview(self):
        self.launch_preview_inputs=self.original_inputs  # Hold before clock/root inspection.
        observation=self.view('native_launch_preview')
        self.launch_preview_return=observation
        return {'plan_pin':copy.deepcopy(self.plan_pin),'original_owner':self.owner,'storage':self,
            'observation':observation,'atomic_reservation':False,'fresh_runtime_closed':False,
            'authenticated_child_owner_transport':False,'native_launch_authorized':False}

    def bind_writer(self,writer):
        self.rejected_writer=writer
        try:
            v.require(self.writer is None,'publication storage original writer once')
            self.writer=writer
            v.require(type(writer) is WorkerGitArchive and writer.checkpoint is self.checkpoint and
                writer.verifier.inventory_pin==self.inventory_pin and writer.verifier.endpoint is self.endpoint and
                type(writer.append_admission) is ArchiveAppendAdmission,'publication storage exact original archive writer')
            writer.original_publication_storage=self
            writer.append_admission.original_publication_storage=self
            self.view('writer_bind')
        except BaseException as error:self._failed(error)

    def bind_carrier(self,carrier):
        self.carriers.append(carrier)  # Before root/clock/native observation.
        try:
            v.require(type(carrier) is PublicationCarrier and carrier.frame_limit==self.allocation['frame_bytes'] and
                carrier.checkpoint is self.checkpoint and (carrier.owner is self.owner or carrier.owner is self.gate),
                'publication storage same original carrier owner and frame bound')
            carrier.native.publication_storage=self
            self.view('carrier_bind')
        except BaseException as error:self._failed(error)


class PublicationCarrier:
    """Bounded original pipe IO; delivered bytes never authenticate child owners.

    This opt-in owns a dedicated creator, not a Git stdout reader. No handle is
    closed or declared released here. A native launcher and cross-process owner
    authentication remain required before parent permission can be granted.
    Synchronous Win IO does not supply a nonblocking or whole-wall guarantee.
    """
    MAGIC=b'PCR1'
    HEADER=40
    MAX_READ_BLOCKS=128

    def __init__(self, *, creator, owner, checkpoint, frame_limit, sending, storage_admission=None):
        self.original_inputs=(creator,owner,checkpoint,frame_limit,sending,storage_admission)
        self.creator,self.owner,self.checkpoint=creator,owner,checkpoint
        self.storage_admission=storage_admission
        self.error=self.original_error=self.pending=self.completion=None
        self.blocks=[];self.raw=b'';self.rejected=None;self.started=False
        try:
            self.previous=getattr(owner,'original_publication_carrier',None)
            if self.previous is not None:
                self.previous.rejected=self
                self.previous._failed(ValueError('carrier original owner cannot be replaced'))
            owner.original_publication_carrier=owner.publication_carrier=self
            from . import anomaly_v03_preformal_job_tree_owner as native
            self.native_api=native
            resources=getattr(creator,'original_publication_resources',None)
            if resources is not None:resources.note_share(self)
            self.kernel=getattr(creator,'kernel',None)
            self.native=getattr(creator,'native',None)
            self.event=getattr(creator,'events',{}).get('stdout')
            v.require(type(creator) is native.NativeGitPipes and creator.result is True and
                creator.error is None and creator.spawn_io is None and self.native.job is None and
                self.native.process is None and self.native.thread is None and
                type(sending) is bool and callable(checkpoint) and type(frame_limit) is int and
                self.HEADER<frame_limit<=proof.channel.MAX_CONTROL,
                'carrier dedicated original creator and caller frame bound')
            self.sending,self.frame_limit=sending,frame_limit
            self.event_raw=io.json_bytes(self.event)
            self.handle=self.event['write' if sending else 'read']
            self.writer=creator.writers['stdout']
            self.api=getattr(self.kernel,'WriteFile' if sending else 'ReadFile')
            self.peek=None if sending else self.kernel.PeekNamedPipe
            prior=getattr(self.native,'publication_carriers',[])
            self.native.publication_carriers=prior+[self]  # Keep rejected aliases on the original creator.
            for previous in prior:
                if previous.sending is sending:
                    previous.rejected=self
                    previous._failed(ValueError('carrier dedicated direction cannot be rebound'))
            v.require(callable(self.api) and (sending or callable(self.peek)), 'carrier original APIs')
            self.binding=(creator,owner,checkpoint,self.kernel,self.native,self.event,self.handle,
                self.writer,self.api,self.peek,frame_limit,sending)
            if storage_admission is not None:
                v.require(type(storage_admission) is PublicationStorageAdmission,'carrier exact storage admission')
                storage_admission.bind_carrier(self)
            self._fixed()
        except BaseException as error:self._failed(error)

    def _failed(self, error):
        if self.original_error is None:self.original_error=error
        self.error=self.original_error
        self.error.publication_carrier=self
        if type(self.owner) is ControlPublicationAdmission:self.owner._failed(self.error)
        remember=getattr(self.owner,'_remember_publication',None)
        if callable(remember):remember(self.error)
        raise self.error

    def _fixed(self):
        if self.original_error is not None:raise self.original_error
        if self.error is not None:raise self.error
        resources=getattr(self.creator,'original_publication_resources',None)
        if resources is not None:
            resources._fixed()
            v.require(not resources.close_started,'carrier cannot use closed publication resources')
        v.require(self.binding==(self.creator,self.owner,self.checkpoint,self.kernel,self.native,self.event,
            self.handle,self.writer,self.api,self.peek,self.frame_limit,self.sending) and
            self.owner.original_publication_carrier is self.owner.publication_carrier is self and
            self.creator.kernel is self.kernel and self.creator.native is self.native and
            self.creator.events['stdout'] is self.event and io.json_bytes(self.event)==self.event_raw and
            self.creator.result is True and self.creator.error is None and self.creator.spawn_io is None and
            self.creator.read_handles['stdout']==self.event['read'] and
            self.creator.writers['stdout'] is self.writer and self.writer.handle==self.event['write'] and
            self.storage_admission is self.original_inputs[5] and
            getattr(self.kernel,'WriteFile' if self.sending else 'ReadFile') is self.api and
            (self.sending or self.kernel.PeekNamedPipe is self.peek),'carrier fixed original IO owner')

    def _checkpoint(self):
        self.checkpoint()
        self._fixed()  # A callback cannot switch a handle/API/owner after observation.
        if self.storage_admission is not None:self.storage_admission.view('carrier_io')

    def _cached(self):
        self._fixed()
        v.require(self.pending is None and self.completion['frame_raw']==self.raw and
            all(self.completion[name] is False for name in ('io_released','parent_ack_authorized',
                'execution_authenticated','atomic_reservation')),'carrier original completed frame')
        evidence._raw(self.raw,self.completion['frame_pin'],'carrier original frame pin')
        if not self.sending:
            v.require(io.json_bytes(self.completion['value'])==self.completion['payload_raw']==self.raw[self.HEADER:],
                'carrier cached original decoded candidate')
        else:
            self.capture._check()
            v.require(self.capture.payload_raw==self.raw[self.HEADER:],'carrier cached original child capture bytes')
        return self.completion

    def unresolved(self):
        try:
            if self.original_error is not None or self.error is not None:
                self.error=self.original_error or self.error
                if type(self.owner) is ControlPublicationAdmission and self.owner.error is None:
                    self.owner.error=self.error
                return True
            self._fixed()
            if self.completion is None:return self.started
            self._cached()
            if self.sending:self.capture._check()
            return False
        except BaseException as error:self._failed(error)

    def send(self, capture):
        self.original_capture_attempt=capture  # Before validation/getters or IO.
        try:
            if self.completion is not None:
                v.require(capture is self.capture,'carrier same original cached capture')
                capture._check();return self._cached()
            self._fixed()
            v.require(not self.started and self.pending is None and not self.blocks,
                'carrier original send attempt cannot be replayed')
            self.started=True
            self.pending={'capture':capture,'creator':self.creator,'native':self.native,'handle':self.handle}
            v.require(self.sending and type(capture) is ChildPublicationCapture and
                capture.gate is self.owner and capture.actor is self.owner.owner,
                'carrier exact sealed child capture')
            self.capture=capture;capture._check()
            payload=self.pending['payload_raw']=capture.payload_raw
            self.raw=self.pending['frame_raw']=self.MAGIC+len(payload).to_bytes(4,'big')+hashlib.sha256(payload).digest()+payload
            v.require(len(self.raw)<=self.frame_limit,'carrier payload plus independent framing bound')
            offset=0;native=self.native_api
            while offset<len(self.raw):
                block={'offset':offset,'raw':self.raw[offset:offset+4096],'handle':self.handle,'kernel':self.kernel}
                self.pending['block']=block;self.blocks.append(block)
                block['buffer']=native.ctypes.create_string_buffer(block['raw'])
                block['count']=native.w.DWORD()
                self._checkpoint();capture._check()
                block['return']=self.api(self.handle,block['buffer'],len(block['raw']),native.ctypes.byref(block['count']),None)
                block['observed_count']=block['count'].value  # Original return/buffer precede checks/clock.
                v.require(type(block['return']) in (int,bool) and bool(block['return']) and
                    block['observed_count']==len(block['raw']),'carrier exact original WriteFile return/count')
                self._checkpoint();capture._check()
                offset+=block['observed_count']
            self.completion={'frame_raw':self.raw,'frame_pin':observed._pin(self.raw),'capture':capture,
                'io_released':False,'parent_ack_authorized':False,'execution_authenticated':False,'atomic_reservation':False}
            self.pending=None;return self.completion
        except BaseException as error:self._failed(error)

    def read_once(self):
        try:
            if self.completion is not None:return self._cached()
            self._fixed();v.require(not self.sending,'carrier original parent reader')
            v.require(self.pending is None,'carrier unresolved original read attempt cannot be replaced')
            self.started=True
            native=self.native_api
            block=self.pending={'handle':self.handle,'kernel':self.kernel,'prefix_bytes':len(self.raw)}
            block['available']=native.w.DWORD()
            self._checkpoint()
            block['peek_return']=self.peek(self.handle,None,0,None,native.ctypes.byref(block['available']),None)
            block['available_count']=block['available'].value
            v.require(type(block['peek_return']) in (int,bool) and bool(block['peek_return']),
                'carrier unknown Peek/EOF cannot supply a completed frame')
            remaining=self.frame_limit-len(self.raw)
            if len(self.raw)>=8:
                v.require(self.raw[:4]==self.MAGIC,'carrier closed frame format')
                size=int.from_bytes(self.raw[4:8],'big')
                v.require(0<size<=self.frame_limit-self.HEADER,'carrier declared payload bound')
                remaining=self.HEADER+size-len(self.raw)
            v.require(0<=block['available_count']<=remaining,'carrier extra data exceeds original frame allowance')
            if block['available_count']==0:
                self._checkpoint();self.pending=None
                if not self.raw:self.started=False
                return None
            amount=min(4096,block['available_count'],remaining)
            v.require(len(self.blocks)<self.MAX_READ_BLOCKS,'carrier bounded retained read attempts')
            block['amount']=amount;block['buffer']=native.ctypes.create_string_buffer(amount)
            block['count']=native.w.DWORD();self.blocks.append(block)
            self._checkpoint()
            block['read_return']=self.api(self.handle,block['buffer'],amount,native.ctypes.byref(block['count']),None)
            block['observed_count']=block['count'].value
            block['read_raw']=block['buffer'].raw[:min(block['observed_count'],amount)]
            v.require(type(block['read_return']) in (int,bool) and bool(block['read_return']) and
                0<block['observed_count']<=amount,'carrier original ReadFile return/count')
            self.raw+=block['read_raw'];self._checkpoint()
            if len(self.raw)<8:self.pending=None;return None
            v.require(self.raw[:4]==self.MAGIC,'carrier closed frame format')
            size=int.from_bytes(self.raw[4:8],'big')
            v.require(0<size<=self.frame_limit-self.HEADER and len(self.raw)<=self.HEADER+size,
                'carrier exact bounded frame length')
            if len(self.raw)<self.HEADER+size:self.pending=None;return None
            payload=block['payload_raw']=self.raw[self.HEADER:]
            v.require(hashlib.sha256(payload).digest()==self.raw[8:self.HEADER],'carrier full raw digest')
            value=block['value']=v.strict_json(payload)
            evidence._keys(value,'format context binding_pin publications raw_bytes parent_ack_authorized execution_authenticated atomic_reservation',
                'carrier closed local candidate')
            v.require(io.json_bytes(value)==payload and value['format']=='anomaly-v03-child-publication-local-capture-v1' and
                all(value[key] is False for key in ('parent_ack_authorized','execution_authenticated','atomic_reservation')),
                'carrier canonical candidate is not parent permission')
            self.completion={'frame_raw':self.raw,'frame_pin':observed._pin(self.raw),'payload_raw':payload,'value':value,
                'io_released':False,'parent_ack_authorized':False,'execution_authenticated':False,'atomic_reservation':False}
            self.pending=None;return self.completion
        except BaseException as error:self._failed(error)


class RequestBootstrapAdmission(ControlPublicationAdmission):
    """Original request publication before an endpoint or inventory pin exists.

    Uses the same retained FileIO return/raw checks as named publications.
    Future slots remain a conservative snapshot gate, never a shared lock.
    """
    def __init__(self, *, root, revision, policy, budget, control_limits, checkpoint, owner):
        self.original_root, self.original_revision, self.original_policy = root, revision, policy
        self.original_budget = self.budget = budget
        self.original_owner = self.owner = owner
        self.original_checkpoint = self.checkpoint = checkpoint
        self.original_controls = control_limits
        self.pending = self.error = self.endpoint = None
        self.completed = {}
        self.generation = {}
        self.previous_bootstrap_owner = None
        try:
            v.require(hasattr(owner,'__dict__'),'request retaining Python owner')
            self.previous_bootstrap_owner=getattr(owner,'request_bootstrap_owner',None)
            if self.previous_bootstrap_owner is not None:
                self.previous_bootstrap_owner.rejected_bootstrap=self
                v.require(False,'request cannot replace original bootstrap owner')
            owner.request_bootstrap_owner=self  # Before copying, validating or observing any native/file value.
            owner.original_request_bootstrap=self
            self.channel_root=Path(root).absolute()
            self.revision, self.policy = copy.deepcopy(revision), copy.deepcopy(policy)
            self.control_limits=copy.deepcopy(control_limits)
            v.require(callable(checkpoint),'request original shared checkpoint')
            evidence._digest(self.revision,40)
            ArchiveAppendAdmission.validate_controls(self.control_limits)
        except BaseException as error:self._failed(error)

    def _failed(self, error):
        if self.error is None:self.error=error
        self.error.request_bootstrap_owner=self
        prior=self.previous_bootstrap_owner
        if type(prior) is RequestBootstrapAdmission and prior.error is None:prior.error=self.error
        preparation=getattr(self.owner,'original_storage_preparation',None)
        if preparation is not None:preparation._failed(self.error)
        raise self.error

    def arm(self, request):
        if self.error is not None:raise self.error
        self.rejected_request=request
        try:
            v.require(not hasattr(self,'request'),'request bootstrap arm once')
            self.original_request=request  # Before canonical encoding, copying, pinning or any checkpoint.
            self.request=copy.deepcopy(request)
            self.root=Path(self.request['budget_root'])
            self.clock=copy.deepcopy(self.request['clock'])
            self.request_raw=io.json_bytes(self.request)
            self.request_pin=observed._pin(self.request_raw)
            v.require(self.request['root']==str(self.channel_root) and self.request['revision']==self.revision and
                self.request['policy_path']==self.policy['path'] and self.request['policy_pin']==self.policy['expected_pin'] and
                self.request['formal_permission'] is False,'request original bootstrap context')
            proof.channel._identity(self.request['parent_identity'])
            evidence._digest(self.request['nonce'],32)
            stat=paths.regular_path(self.root,directory=True).lstat()
            self.identity=(stat.st_dev,stat.st_ino)
            self.plan_raw=self._plan()
        except BaseException as error:self._failed(error)

    def _plan(self):
        return io.json_bytes({'request_pin':self.request_pin,'root':str(self.root),
            'channel_root':str(self.channel_root),'root_identity':list(self.identity),
            'control_limits':self.control_limits,'clock':self.clock})

    def _view(self, stage):
        self.checkpoint()
        preparation=getattr(self.owner,'original_storage_preparation',None)
        if preparation is not None:preparation.view('request_'+stage)
        v.require(self.owner is self.original_owner and self.owner.request_bootstrap_owner is self and
            self.budget is self.original_budget and self.checkpoint is self.original_checkpoint and
            self._plan()==self.plan_raw and io.json_bytes(self.request)==self.request_raw and
            self.budget.started_at==self.clock['started_at'] and
            self.budget.limits['wall_seconds']==self.clock['wall_seconds'] and
            self.request['root_identity']==proof.channel._directory_identity(self.channel_root),
            'request original owner, clock, directory or plan changed')
        if self.endpoint is not None:
            v.require(self.endpoint is self.original_returned_endpoint and self.endpoint.request_bootstrap_owner is self and
                self.endpoint.request_pin==self.request_pin and io.json_bytes(self.endpoint.request)==self.request_raw,
                'request original returned endpoint link')
        from . import anomaly_v03_preformal_generated_chain_budget as monitor
        snapshot=monitor._directory_snapshot(self.root,32,2,self.identity)
        held={'snapshot':snapshot,'controls':{}}
        self.pending[stage]=held
        for name,maximum in self.control_limits.items():
            path=self.channel_root/name
            paths.regular_path(path,missing=True)
            info=path.lstat() if path.exists() else None
            held['controls'][name]=None if info is None else {'bytes':info.st_size,'identity':(info.st_dev,info.st_ino)}
            v.require(info is None or info.st_size<=maximum,'request retained control exceeds original maximum')
            if name=='request.json.pending' and 'request.json' in self.completed:
                v.require(info is None,'request unknown pending after original publication')
        # No discount for bytes observed before another writer publishes.
        held.update(future_bytes=sum(self.control_limits.values()),future_entries=len(self.control_limits))
        v.require(snapshot['directory_bytes']+held['future_bytes']+128*1024<=1024**2 and
            snapshot['directory_entries']+held['future_entries']+2<=32,
            'request future control slots exceed original outer reserve')

    def publish(self, path, value):
        if self.error is not None:raise self.error
        self.rejected_publication=(path,value)
        try:
            v.require(Path(path)==self.channel_root/'request.json' and value is self.original_request,
                      'request bootstrap publishes original request only')
            return super().publish(path,value)
        except BaseException as error:self._failed(error)

    def attach(self, endpoint):
        if self.error is not None:raise self.error
        self.rejected_endpoint=endpoint  # Before endpoint checks or disk readback.
        try:
            v.require(self.endpoint is None,'request bootstrap endpoint attach once')
            self.original_returned_endpoint=endpoint
            v.require(isinstance(endpoint,proof.channel.ParentChannel) and
                endpoint.root==self.channel_root and endpoint.request_pin==self.request_pin and
                io.json_bytes(endpoint.request)==self.request_raw,
                'request endpoint formed from original observed publication')
            self.endpoint=endpoint
            endpoint.request_bootstrap_owner=self
            self.verify_publications(('request.json',))
        except BaseException as error:self._failed(error)


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
    def __init__(self, *, path, verifier, checkpoint, append_admission=None, storage_admission=None):
        self.original_storage_input=storage_admission
        self.original_append_admission = self.append_admission = append_admission
        v.require(callable(checkpoint), 'worker archive shared budget checkpoint required')
        self.verifier, self.checkpoint = verifier, checkpoint
        self.inventory_raw = _inventory(verifier)
        self.path = _path(path, verifier.endpoint)
        v.require(not self.path.exists(), 'worker archive exclusive unused file')
        self.rows, self.raw, self.statuses = [], b'', []
        self.pending, self.failed = None, False
        if append_admission is not None:
            v.require(type(append_admission) is ArchiveAppendAdmission, 'worker archive explicit append admission')
            append_admission.bind(self)
        if storage_admission is not None:storage_admission.bind_writer(self)
        checkpoint(); verifier._live()
        if storage_admission is None:io._exclusive(self.path, b'')
        else:self._storage_empty(storage_admission)
        checkpoint()

    def _storage_empty(self,storage):
        held=self.initial_pending={'path':self.path,'storage':storage,'raw':b'',
            'file_factory':proof.tree.file_io.FileIO}
        try:
            storage.view('archive_before_create')
            held['stream']=stream=held['file_factory'](self.path,'xb')
            held['fd']=fd=stream.fileno()
            held['initial_stat']=info=os.fstat(fd)
            held['identity']=(info.st_dev,info.st_ino)
            held['path_stat']=path_info=self.path.lstat()
            v.require(info.st_size==0 and info.st_ino>0 and stream.closefd is True and
                held['identity']==(path_info.st_dev,path_info.st_ino),
                'archive original exclusive empty fd/path')
            stream.flush();os.fsync(fd)
            held['synced_stat']=info=os.fstat(fd)
            v.require(info.st_size==0 and (info.st_dev,info.st_ino)==held['identity'],'archive initial original fd sync')
            held['close_return']=stream.close();held['close_return_observed']=True
            v.require(held['close_return'] is None and stream.closed is True,'archive original Python close return')
            held['readback']=observed._file(self.path,MAX_BYTES)
            held['post_stat']=path_info=self.path.lstat()
            v.require(held['readback']==b'' and (path_info.st_dev,path_info.st_ino)==held['identity'],
                'archive original empty full readback')
            storage.view('archive_after_create')
            self.initial_completion=held;self.initial_pending=None
        except BaseException as error:
            self.failed=True;held['error']=error;storage._failed(error)

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
            self.pending['encoded'] = encoded
            v.require(len(encoded) <= MAX_RAW, 'worker archive decoded record byte bound')
            compressed = gzip.compress(encoded,mtime=0)
            self.pending['compressed'] = compressed
            v.require(len(compressed) <= MAX_RECORD, 'worker archive compressed record byte bound')
            frame = MAGIC+len(compressed).to_bytes(4,'big')+compressed
            self.pending['frame'] = frame
            candidate = self.raw+frame
            self.pending['candidate'] = candidate
            v.require(len(candidate) <= MAX_BYTES, 'worker archive existing total byte bound')
            row = {'lease':lease,'offset':len(self.raw),**observed._pin(frame),
                   'evidence_pin':copy.deepcopy(checked['evidence_pin'])}
            rows = self.rows+[row]
            manifest = self._manifest(candidate,rows)
            self.pending['manifest'] = manifest
            if self.append_admission is not None:
                self.append_admission.reserve(self,lease,frame)
            self.failed = True  # No append retry after any uncertain write/readback.
            self.checkpoint(); _append_frame(self.path,frame)
            saved = SavedWorkerGitArchive(endpoint=self.verifier.endpoint,
                manifest_raw=manifest,manifest_pin=observed._pin(manifest),
                inventory_raw=self.inventory_raw,inventory_pin=self.verifier.inventory_pin,
                checkpoint=self.checkpoint)
            v.require(saved.read(lease) == packet and self.verifier.record(lease)[0] == checked,
                      'worker archive saved/original raw readback')
            self.checkpoint()
            if self.append_admission is not None:
                self.append_admission.complete(self)
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
