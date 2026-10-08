"""Own invented Windows CLI trees with private Job Objects.

Job accounting confirms that every process *in this job* has exited. It does
not authenticate individual descendant exit codes, processes created outside
the job, or a whole-tree S4 resource budget.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_process_supervisor as direct_supervisor
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_runtime as paths


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'tests' / 'fixtures' / 'anomaly_v03_job_tree_child.py'
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
STILL_ACTIVE = 259
STARTF_USESTDHANDLES = 0x00000100
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
DUPLICATE_SAME_ACCESS = 0x00000002


class _BasicLimit(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64),
                ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', w.DWORD),
                ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t),
                ('ActiveProcessLimit', w.DWORD),
                ('Affinity', ctypes.c_size_t),
                ('PriorityClass', w.DWORD),
                ('SchedulingClass', w.DWORD)]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
        'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class _ExtendedLimit(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', _BasicLimit),
                ('IoInfo', _IoCounters),
                ('ProcessMemoryLimit', ctypes.c_size_t),
                ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t),
                ('PeakJobMemoryUsed', ctypes.c_size_t)]


class _BasicAccounting(ctypes.Structure):
    _fields_ = [('TotalUserTime', ctypes.c_int64),
                ('TotalKernelTime', ctypes.c_int64),
                ('ThisPeriodTotalUserTime', ctypes.c_int64),
                ('ThisPeriodTotalKernelTime', ctypes.c_int64),
                ('TotalPageFaultCount', w.DWORD),
                ('TotalProcesses', w.DWORD),
                ('ActiveProcesses', w.DWORD),
                ('TotalTerminatedProcesses', w.DWORD)]


class _StartupInfo(ctypes.Structure):
    _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR),
                ('lpDesktop', w.LPWSTR), ('lpTitle', w.LPWSTR),
                ('dwX', w.DWORD), ('dwY', w.DWORD),
                ('dwXSize', w.DWORD), ('dwYSize', w.DWORD),
                ('dwXCountChars', w.DWORD), ('dwYCountChars', w.DWORD),
                ('dwFillAttribute', w.DWORD), ('dwFlags', w.DWORD),
                ('wShowWindow', w.WORD), ('cbReserved2', w.WORD),
                ('lpReserved2', ctypes.POINTER(w.BYTE)),
                ('hStdInput', w.HANDLE), ('hStdOutput', w.HANDLE),
                ('hStdError', w.HANDLE)]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE),
                ('dwProcessId', w.DWORD), ('dwThreadId', w.DWORD)]


class _StartupInfoEx(ctypes.Structure):
    _fields_ = [('StartupInfo', _StartupInfo),
                ('lpAttributeList', ctypes.c_void_p)]


class UnreapedJob(RuntimeError):
    """The caller retains native handles when all job members are unconfirmed."""

    def __init__(self, job, process, thread, report, extra_handles=None):
        self.job, self.process, self.thread, self.report = job, process, thread, report
        self.extra_handles = dict(extra_handles or {})
        self.original_error = self.stop_error = None
        self.cleanup_error = self.attributes = None
        self.attribute_list_cleanup_pending = False
        self.unknown_close_handles = ()
        super().__init__('owned Job process exit could not be confirmed')


class UnclosedHandles(RuntimeError):
    """Preserve exact native handles if CloseHandle fails."""

    def __init__(self, handles, report):
        self.handles, self.report = dict(handles), report
        self.close_error = self.diagnostic_error = None
        super().__init__('owned Job handles could not all be closed')


class NativePipeWriter:
    """Caller-owned raw pipe HANDLE; no file descriptor or destructor closes it."""
    def __init__(self, handle):
        self.handle = handle


class PublicationPipeResources:
    """Retain one issuer and four dedicated handles before worker launch.

    Only unshared, never-spawned resources can be closed here. This is not a
    child transport, a process launcher or an authenticated recovery proof.
    """
    def __init__(self, issuer, *, checkpoint, owner):
        self.original_inputs=(issuer,checkpoint,owner)
        self.issuer,self.checkpoint,self.owner=issuer,checkpoint,owner
        self.native=UnreapedJob(None,None,None,{'phase':'publication_pipe_resources','formal_permission':False})
        self.native.publication_resources=self
        self.original_error=self.error=self.pending=self.result=self.creator=self.retention_error=None
        self.issue_started=self.close_started=False
        self.close_completion=None;self.close_events={};self.close_return_bindings={}
        self.rejected=None;self.original_shares=()
        try:
            self.previous=getattr(owner,'original_publication_resources',None)
            if self.previous is not None:
                self.previous.rejected=self
                self.previous._failed(ValueError('publication resources cannot replace original owner'))
            owner.original_publication_resources=owner.publication_resources=self
            resources.rt.require(callable(issuer) and callable(checkpoint),'publication original issuer/checkpoint')
            self._fixed()
        except BaseException as error:self._failed(error)

    def _failed(self,error):
        if self.original_error is None:self.original_error=error
        self.error=self.original_error
        self.error.publication_resources=self
        self.native.original_error=self.error
        try:
            remember=getattr(self.owner,'_remember_publication',None)
            if callable(remember):remember(self.error)
        except BaseException as diagnostic:
            if self.retention_error is None:self.retention_error=diagnostic
        raise self.error

    def _fixed(self):
        if self.original_error is not None:raise self.original_error
        inheritance=getattr(self,'original_publication_inheritance',None)
        if inheritance is not None:
            resources.rt.require(self.publication_inheritance is inheritance and inheritance.resources is self and
                inheritance.owner.original_publication_inheritance is inheritance.owner.publication_inheritance is inheritance,
                'publication original inheritance owner cannot be hidden')
            if inheritance.original_error is not None:raise inheritance.original_error
        resources.rt.require(self.original_inputs==(self.issuer,self.checkpoint,self.owner) and
            self.owner.original_publication_resources is self.owner.publication_resources is self,
            'publication original resource owner and issuer cannot be hidden')
        if hasattr(self,'original_issue_result'):
            resources.rt.require(self.result is self.original_issue_result,'publication original issued return cannot be hidden')
        if hasattr(self,'original_close_owner'):
            resources.rt.require(self.close_owner is self.original_close_owner and self.close_started is True,
                'publication original close owner cannot be hidden or reset')
            resources.rt.require(set(self.close_events)==set(self.close_return_bindings) and
                all((r['handle'],r['return'],r['return_observed'],r['api'])==self.close_return_bindings[n]
                    for n,r in self.close_events.items()),'publication original named close events cannot follow callbacks')
        if self.result is not None:
            resources.rt.require(self.creator is self.result['creator'] and self.kernel is self.result['kernel'] and
                self.creator.original_publication_resources is self and self.creator.kernel is self.kernel and
                self.creator.checkpoint is self.checkpoint and self.creator.native is self.original_creator_native and
                self.creator.result is True and self.creator.error is None and self.creator.spawn_io is None and
                self.creator.native.job is self.creator.native.process is self.creator.native.thread is None and
                self.kernel.CreatePipe is self.create_api and self.kernel.CloseHandle is self.close_api and
                self.creator.events==self.original_events and self.creator.read_handles==self.original_reads and
                all(self.creator.writers[n] is writer and writer.handle==self.handles[n+'_write']
                    for n,writer in self.original_writers.items()) and
                self.result['creation_return'] is self.creation_return and
                self.creation_return==self.original_events and tuple(self.handles.items())==self.original_handles and
                tuple((n,tuple(sorted(row.items()))) for n,row in self.creation_return.items())==self.creation_snapshot and
                all(self.result[n] is False for n in ('native_launch_authorized','parent_ack_authorized')),
                'publication fixed original APIs, creation returns and dedicated handles')
        if hasattr(self,'original_close_completion'):
            resources.rt.require(self.close_completion is self.original_close_completion and
                self.close_completion['closed_handles']==dict(self.original_handles) and
                self.close_completion['original_returns']==self.close_events and
                tuple((n,r['handle'],r['return'],r['return_observed'],r['api']) for n,r in self.close_events.items())==self.close_snapshot and
                all(self.close_completion[n] is False for n in ('native_owner_recovered','parent_ack_authorized','execution_authenticated')),
                'publication original cached close returns cannot be changed')

    def issue(self):
        try:
            self._fixed();resources.rt.require(not self.close_started,'publication closed resources cannot be issued')
            if self.result is not None:return self.result
            resources.rt.require(self.pending is None and not self.issue_started,'publication issuer cannot be retried')
            self.issue_started=True
            self.pending={'issuer':self.issuer,'owner':self.owner,'native':self.native,'stage':'issuer'}
            self.checkpoint();self._fixed()
            self.pending['issuer_return']=self.kernel=self.issuer()  # Before getter/copy/clock IO.
            self.create_api=self.kernel.CreatePipe;self.close_api=self.kernel.CloseHandle
            resources.rt.require(callable(self.create_api) and callable(self.close_api),'publication original kernel APIs')
            self.creator=NativeGitPipes.__new__(NativeGitPipes)  # Hold before its constructor and CreatePipe.
            self.pending['creator']=self.creator
            self.creator.__init__(self.kernel,checkpoint=self.checkpoint)
            self.creator.original_publication_resources=self
            self.original_creator_native=self.creator.native;self.native.pipe_successor=self.creator.native
            self.creation_return=self.pending['creation_return']=self.creator.create()
            self.original_events={n:dict(row) for n,row in self.creator.events.items()}
            self.original_reads=dict(self.creator.read_handles);self.original_writers=dict(self.creator.writers)
            self.handles={key:row[direction] for name,row in self.original_events.items()
                for direction,key in [('read',name+'_read'),('write',name+'_write')]}
            self.original_handles=tuple(self.handles.items())
            self.creation_snapshot=tuple((n,tuple(sorted(row.items()))) for n,row in self.creation_return.items())
            resources.rt.require(len(self.handles)==len(set(self.handles.values()))==4,
                'publication original four distinct handles, separate from inherited stdio')
            self.native.extra_handles=dict(self.handles)  # Keep original names even after known close returns.
            self.result={'creator':self.creator,'kernel':self.kernel,'creation_return':self.creation_return,
                'native_launch_authorized':False,'parent_ack_authorized':False}
            self.original_issue_result=self.result
            self.checkpoint();self._fixed();self.pending=None
            return self.result
        except BaseException as error:self._failed(error)

    def close_unlaunched(self):
        self.rejected_close_attempt=(self.creator,self.owner)
        if not hasattr(self,'original_close_attempt'):self.original_close_attempt=self.rejected_close_attempt
        try:
            self._fixed()
            if self.close_completion is not None:return self.close_completion
            resources.rt.require(self.result is not None and not self.close_started and self.pending is None,
                'publication original close starts once after complete issue')
            self.close_started=True
            self.close_owner=UnclosedHandles(self.handles,{'phase':'unlaunched_publication_pipe_close','formal_permission':False})
            self.original_close_owner=self.close_owner
            self.close_owner.publication_resources=self
            self.pending={'owner':self.close_owner,'creator':self.creator,'handles':dict(self.handles)}
            self.pending['caller_worker']=getattr(self.owner,'worker',None)
            self.pending['endpoint']=endpoint=getattr(self.owner,'parent',None)
            self.pending['endpoint_worker']=getattr(endpoint,'worker',None)
            resources.rt.require(self.pending['caller_worker'] is None and self.pending['endpoint_worker'] is None and
                not self.original_shares and
                not getattr(self.creator.native,'publication_carriers',[]) and
                not hasattr(self.creator.native,'reader_publication_launch'),
                'publication close only before any Popen, launch preparation or carrier sharing')
            for name,handle in self.handles.items():
                self.checkpoint();self._fixed()
                row=self.pending['call']={'name':name,'handle':handle,'api':self.close_api,'return_observed':False}
                binding=self.pending['call_binding']=(name,handle,self.close_api)
                row['return']=closed=self.close_api(handle)  # Original return before count/clock/diagnostics.
                row['return_observed']=True
                resources.rt.require((row['name'],row['handle'],row['api'])==binding==self.pending['call_binding'],
                    'publication original close call binding changed during API')
                resources.rt.require(type(closed) in (int,bool),'publication CloseHandle original BOOL return')
                if not closed:raise OSError('publication CloseHandle returned False')
                self.close_events[name]=row
                self.close_return_bindings[name]=(handle,closed,True,self.close_api)
                self.close_owner.handles.pop(name)
                self.checkpoint();self._fixed()
            self.close_completion={'closed_handles':dict(self.handles),'original_returns':dict(self.close_events),
                'native_owner_recovered':False,'parent_ack_authorized':False,'execution_authenticated':False}
            self.original_close_completion=self.close_completion
            self.close_snapshot=tuple((n,r['handle'],r['return'],r['return_observed'],r['api']) for n,r in self.close_events.items())
            self.pending=None
            return self.close_completion
        except BaseException as error:
            held=getattr(self,'close_owner',None)
            if held is not None:
                if held.close_error is None:held.close_error=error
                self.native.unknown_close_handles=tuple(held.handles)
                self._failed(held)
            self._failed(error)

    def note_share(self,owner):
        self.rejected_share=owner  # Keep rejected resources before validation.
        try:
            self._fixed();resources.rt.require(not self.close_started,'publication closed resources cannot be shared')
            if not any(value is owner for value in self.original_shares):
                resources.rt.require(len(self.original_shares)<4,'publication original share bound')
                self.original_shares+= (owner,)
        except BaseException as error:self._failed(error)

    def unresolved(self):
        try:
            self._fixed()
            inheritance=getattr(self,'original_publication_inheritance',None)
            return self.pending is not None or (inheritance is not None and
                (inheritance.pending is not None or inheritance.close_started))
        except BaseException as error:
            if self.original_error is None:self.original_error=error
            self.error=self.original_error;return True


class PublicationPipeInheritance:
    """Keep two caller-local inheritable duplicates separate from stdio.

    The offer is a Python tuple, not a child transport or a launch permit.
    Binding a Popen records the original association, never proves inheritance.
    """
    def __init__(self, original_resources, *, owner):
        self.original_inputs=(original_resources,owner)
        self.resources,self.owner=original_resources,owner
        self.native=UnreapedJob(None,None,None,{'phase':'publication_pipe_inheritance','formal_permission':False})
        self.native.publication_inheritance=self
        self.original_error=self.error=self.pending=self.result=self.retention_error=None
        self.started=self.close_started=False
        self.events={};self.event_bindings={};self.close_events={};self.close_bindings={}
        self.call_bindings={};self.original_call_order=()
        self.native.duplicate_call_bindings=self.call_bindings
        self.original_close_returns=()
        self.offered=self.process=self.worker_binding=self.close_completion=self.rejected=None
        try:
            resources.rt.require(type(original_resources) is PublicationPipeResources,
                'publication inheritance requires original resource issuance')
            previous=getattr(original_resources,'original_publication_inheritance',None)
            if previous is not None:
                previous.rejected=self
                previous._failed(ValueError('publication inheritance cannot replace original owner'))
            original_resources.original_publication_inheritance=original_resources.publication_inheritance=self
            owner.original_publication_inheritance=owner.publication_inheritance=self
            original_resources.native.publication_inheritance=self
            self.pending={'resources':original_resources,'owner':owner,'native':self.native,'stage':'APIs'}
            original_resources._fixed()
            resources.rt.require(type(original_resources) is PublicationPipeResources and
                original_resources.result is not None and not original_resources.close_started and
                original_resources.pending is None,'publication original fully issued resources')
            self.creator=original_resources.creator;self.kernel=original_resources.kernel
            self.checkpoint=original_resources.checkpoint
            self.get_process_api=self.kernel.GetCurrentProcess
            self.duplicate_api=self.kernel.DuplicateHandle;self.close_api=original_resources.close_api
            resources.rt.require(callable(self.get_process_api) and callable(self.duplicate_api),
                'publication original duplicate APIs')
            self.source_handles=tuple((name,original_resources.handles[name+'_write']) for name in ('stdout','stderr'))
            original_resources.note_share(self)
            self._fixed();self.pending=None
        except BaseException as error:self._failed(error)

    def _failed(self,error):
        if self.original_error is None:self.original_error=error
        self.error=self.original_error;self.error.publication_inheritance=self
        if self.native.original_error is None:self.native.original_error=self.error
        if type(self.resources) is PublicationPipeResources:
            self.resources._failed(self.error)  # Original parent retention; diagnostics cannot replace it.
        try:
            remember=getattr(self.owner,'_failed',None)
            if callable(remember):remember(self.error)
        except BaseException as diagnostic:
            if diagnostic is not self.error:self.retention_error=diagnostic
        raise self.error

    def _fixed(self):
        if self.original_error is not None:raise self.original_error
        self.resources._fixed()
        if hasattr(self,'original_process_return'):
            resources.rt.require(self.process_handle==self.original_process_return,
                'publication original current process return cannot change')
        resources.rt.require(self.resources is self.original_inputs[0] and self.owner is self.original_inputs[1] and
            self.resources.original_publication_inheritance is self.resources.publication_inheritance is self and
            self.owner.original_publication_inheritance is self.owner.publication_inheritance is self and
            self.creator is self.resources.creator and self.kernel is self.resources.kernel and
            self.checkpoint is self.resources.checkpoint and not self.resources.close_started and
            self.kernel.GetCurrentProcess is self.get_process_api and self.kernel.DuplicateHandle is self.duplicate_api and
            self.kernel.CloseHandle is self.close_api and
            self.source_handles==tuple((n,self.resources.handles[n+'_write']) for n in ('stdout','stderr')) and
            self.creator.spawn_io is None and self.creator.native.job is self.creator.native.process is self.creator.native.thread is None,
            'publication fixed original duplicate resources, APIs and sources')
        resources.rt.require(set(self.events)==set(self.event_bindings) and all(
            (r['source'],r['duplicate'],r['return'],r['return_observed'],r['api'],r['process'],r['output'])==self.event_bindings[n]
            and r['output'].value==r['duplicate'] for n,r in self.events.items()),
            'publication original duplicate returns and output buffers cannot follow callbacks')
        resources.rt.require(tuple(self.call_bindings.values())==self.original_call_order and
            len(self.original_call_order)<=2,'publication original duplicate call tuples cannot be hidden')
        if hasattr(self,'original_result'):
            resources.rt.require(self.result is self.original_result and
                self.result['dedicated_handles']==self.original_duplicates and self.result['source_handles']==self.source_handles and
                tuple((n,r['duplicate']) for n,r in self.events.items())==self.original_duplicates and
                self.result['dedicated_count']==2 and self.result['stdio_slots_used']==0 and
                all(self.result[k] is False for k in ('native_launch_authorized','inheritance_observed','parent_ack_authorized','execution_authenticated')),
                'publication duplicate offer is separate from inherited stdio and permissions')
        if hasattr(self,'original_offer'):
            resources.rt.require(self.offered is self.original_offer and self.offered==self.original_duplicates,
                'publication original offered HANDLE tuple cannot be hidden')
        if self.worker_binding is not None:
            resources.rt.require(self.worker_binding is self.original_worker_binding and
                self.worker_binding['process'] is self.process is self.owner.process and
                self.worker_binding['process_handle']==self.original_worker_inputs[1] and
                self.worker_binding['creation'] is self.original_worker_inputs[2] and
                tuple(sorted(self.worker_binding['creation'].items()))==self.creation_snapshot and
                self.worker_binding['context_raw']==self.original_worker_inputs[3]==self.owner.context_wrapper_raw and
                self.worker_binding['dedicated_handles'] is self.original_offer and
                self.worker_binding['inheritance_observed'] is False and self.worker_binding['execution_authenticated'] is False,
                'publication original Popen association is not authenticated inheritance')
        resources.rt.require(set(self.close_events)==set(self.close_bindings) and all(
            (r['handle'],r['return'],r['return_observed'],r['api'])==self.close_bindings[n]
            for n,r in self.close_events.items()),'publication original duplicate close returns')
        resources.rt.require(tuple((n,r['handle'],r['return'],r['return_observed'],r['api'])
            for n,r in self.close_events.items())==self.original_close_returns,
            'publication original close return ledger cannot be hidden')
        if hasattr(self,'original_close_completion'):
            resources.rt.require(self.close_completion is self.original_close_completion and
                self.close_completion['closed_handles']==dict(self.original_duplicates) and
                self.close_completion['original_returns']==self.close_events and
                all(self.close_completion[k] is False for k in ('native_owner_recovered','parent_ack_authorized','execution_authenticated')),
                'publication local duplicate close is not native recovery')

    def prepare(self):
        try:
            self._fixed();resources.rt.require(not self.close_started,'publication closed duplicates cannot be prepared')
            if self.result is not None:return self.result
            resources.rt.require(not self.started and self.pending is None,'publication duplicate cannot be retried')
            self.started=True
            self.pending={'resources':self.resources,'owner':self.owner,'native':self.native,'stage':'current_process','api':self.get_process_api}
            self.checkpoint();self._fixed()
            self.pending['process_return']=self.process_handle=self.original_process_return=self.get_process_api()
            resources.rt.require(type(self.process_handle) is int and self.process_handle!=0,
                'publication original current process return')
            for name,source in self.source_handles:
                output=w.HANDLE()
                row=self.pending={'name':name,'source':source,'api':self.duplicate_api,'process':self.process_handle,
                    'output':output,'inheritable':True,'desired_access':0,'options':2,
                    'return_observed':False,'output_indeterminate':True,'native':self.native,'owner':self.owner}
                binding=self.pending_binding=(name,source,self.duplicate_api,self.process_handle,output,True,0,2)
                self.call_bindings[name]=binding;self.original_call_order+=(binding,)
                self.checkpoint();self._fixed()
                row['return']=returned=binding[2](binding[3],binding[1],binding[3],
                    ctypes.byref(binding[4]),binding[6],binding[5],binding[7])
                row['return_observed']=True;row['observed_output']=output.value
                if type(returned) in (int,bool) and returned:
                    row['output_indeterminate']=False
                    self.native.extra_handles[name]=output.value  # Before callback binding validation.
                resources.rt.require((row['name'],row['source'],row['api'],row['process'],row['output'],
                    row['inheritable'],row['desired_access'],row['options'])==binding==self.pending_binding,
                    'publication original duplicate call binding changed during API')
                resources.rt.require(type(returned) in (int,bool),'publication DuplicateHandle original BOOL')
                if not returned:raise OSError('publication DuplicateHandle returned False')
                row['duplicate']=output.value
                self.events[name]=row
                self.event_bindings[name]=(source,output.value,returned,True,self.duplicate_api,self.process_handle,output)
                values=tuple(self.native.extra_handles.values())
                resources.rt.require(all(type(h) is int and 0<h<2**64 for h in values) and
                    len(set(values))==len(values) and not set(values)&set(self.resources.handles.values()),
                    'publication distinct caller-owned duplicate handles')
                self.checkpoint();self._fixed()
            self.original_duplicates=tuple(self.native.extra_handles.items())
            self.result={'dedicated_handles':self.original_duplicates,'source_handles':self.source_handles,
                'dedicated_count':2,'stdio_slots_used':0,'native_launch_authorized':False,
                'inheritance_observed':False,'parent_ack_authorized':False,'execution_authenticated':False}
            self.original_result=self.result;self.pending=None;self._fixed();return self.result
        except BaseException as error:self._failed(error)

    def offer(self):
        try:
            self._fixed();resources.rt.require(self.result is not None and self.pending is None and
                not self.close_started and self.offered is None,'publication original launch offer once')
            self.offered=self.original_offer=self.original_duplicates
            return self.offered  # No JSON, CreateProcess, attribute list or transport issuance.
        except BaseException as error:self._failed(error)

    def bind_worker(self,process,process_handle,creation,context_raw):
        self.rejected_worker_inputs=(process,process_handle,creation,context_raw)  # Before Popen/context getters.
        try:
            self._fixed();resources.rt.require(self.process is None and self.offered is not None and
                self.pending is None and not self.close_started,'publication original offered worker bind once')
            self.original_worker_inputs=self.rejected_worker_inputs
            self.process=process
            self.pending={'process':process,'process_handle':process_handle,'creation':creation,
                'context_raw':context_raw,'owner':self.owner,'dedicated_handles':self.original_offer}
            held=self.pending;binding=self.owner.parent.publication_carrier_binding
            held['binding']=binding
            self.creation_snapshot=tuple(sorted(creation.items()))
            resources.rt.require(process is self.owner.process is self.owner.parent.worker is binding['process'] and
                process_handle==binding['process_handle'] and creation is self.owner.pending['creation_return'] and
                creation==binding['creation'] and context_raw==self.owner.context_wrapper_raw,
                'publication same original Popen HANDLE, creation return and caller context')
            self.worker_binding=self.original_worker_binding={**held,'inheritance_observed':False,'execution_authenticated':False}
            self.pending=None;self._fixed();return self.worker_binding
        except BaseException as error:self._failed(error)

    def close_before_offer(self):
        try:
            self._fixed()
            if self.close_completion is not None:return self.close_completion
            resources.rt.require(self.result is not None and self.pending is None and not self.close_started,
                'publication original local duplicate close once')
            self.close_started=True
            self.close_owner=UnclosedHandles(dict(self.original_duplicates),{'phase':'publication_local_duplicate_close','formal_permission':False})
            self.native.local_duplicate_close_owner=self.close_owner
            self.pending={'owner':self.close_owner,'resources':self.resources,'launch_owner':self.owner}
            self.pending['caller_process']=getattr(self.owner,'process',None)
            resources.rt.require(self.offered is None and not hasattr(self,'original_offer') and self.process is None and
                self.pending['caller_process'] is None,'publication duplicate close only before launch offer or Popen')
            for name,handle in self.original_duplicates:
                row=self.pending['call']={'name':name,'handle':handle,'api':self.close_api,'return_observed':False}
                binding=self.pending['call_binding']=(name,handle,self.close_api)
                self.checkpoint();self._fixed()
                row['return']=returned=self.close_api(handle);row['return_observed']=True
                resources.rt.require((row['name'],row['handle'],row['api'])==binding==self.pending['call_binding'],
                    'publication original duplicate close binding changed')
                resources.rt.require(type(returned) in (int,bool),'publication duplicate CloseHandle original BOOL')
                if not returned:raise OSError('publication duplicate CloseHandle returned False')
                self.close_events[name]=row;self.close_bindings[name]=(handle,returned,True,self.close_api)
                self.original_close_returns+=(name,handle,returned,True,self.close_api),
                self.close_owner.handles.pop(name)
                self.checkpoint();self._fixed()
            self.close_completion=self.original_close_completion={'closed_handles':dict(self.original_duplicates),
                'original_returns':dict(self.close_events),'native_owner_recovered':False,
                'parent_ack_authorized':False,'execution_authenticated':False}
            self.pending=None;self._fixed();return self.close_completion
        except BaseException as error:
            held=getattr(self,'close_owner',None)
            if held is not None:
                if held.close_error is None:held.close_error=error
                self.native.unknown_close_handles=tuple(held.handles)
                self._failed(held)
            self._failed(error)


class NativeGitPipes:
    """Retain anonymous-pipe creation before a Job/process exists.

    Failed CreatePipe output parameters are indeterminate, not closeable
    handles. This owner neither closes resources nor permits a lease/ack.
    A caller must keep its Python alive on an unresolved native exception.
    Root/output admission and the executor transport remain separate.
    """
    def __init__(self, kernel, *, checkpoint):
        self.kernel, self.checkpoint = kernel, checkpoint
        self.native = UnreapedJob(None,None,None,{
            'status':'pending','phase':'git_pipe_creation','formal_permission':False})
        self.native.pipe_creator = self
        self.pending = self.error = self.result = self.spawn_io = None
        self.original_sinks = self.sinks = self.rejected_sinks = None
        self.events, self.read_handles, self.writers = {}, {}, {}
        self.started = False
        try:
            resources.rt.require(callable(checkpoint) and
                callable(getattr(kernel,'CreatePipe',None)), 'Git pipe original kernel/checkpoint')
        except BaseException as failure:
            self._failed(failure)

    def _failed(self, failure):
        if self.error is None:
            self.error = failure
        retained = self.spawn_io.native if self.spawn_io is not None else self.native
        retained.pipe_creator = self
        retained.pipe_creation_error = self.error
        if retained.original_error is None:
            retained.original_error = self.error
        raise retained from self.error

    def create(self):
        publication=getattr(self,'original_publication_resources',None)
        if publication is not None:
            publication._fixed()
            resources.rt.require(not publication.close_started and
                (not hasattr(publication,'original_issue_result') or not publication.unresolved()),
                'closed or unresolved publication pipes cannot be reused')
        if self.error is not None:
            self._failed(self.error)
        if self.result is not None:
            return {name:dict(event) for name,event in self.events.items()}
        try:
            resources.rt.require(not self.started, 'Git pipes cannot be rearmed')
            self.started = True
            handles = []
            for name in ('stdout','stderr'):
                read, write = w.HANDLE(), w.HANDLE()
                self.pending = {'name':name,'read':read,'write':write,'kernel':self.kernel,
                    'security_attributes':None,'buffer_hint':4096,'return':None,
                    'out_parameters_indeterminate':True}
                self.checkpoint()
                self.pending['return'] = result = self.kernel.CreatePipe(
                    ctypes.byref(read),ctypes.byref(write),None,4096)
                # Keep both original output buffers even when the API fails/interrupts.
                self.pending['observed_values'] = {'read':read.value,'write':write.value}
                resources.rt.require(type(result) in (int,bool), 'Git CreatePipe native return')
                if not result:
                    self.pending['last_error'] = ctypes.get_last_error()
                    raise OSError(self.pending['last_error'], 'Git CreatePipe')
                self.pending['out_parameters_indeterminate'] = False
                event={'api':'CreatePipe','return':int(result),'read':read.value,'write':write.value,
                       'security_attributes':None,'buffer_hint':4096,'kernel_buffer_bound_proven':False}
                self.events[name] = event  # Before validation or post-call clock/diagnostic IO.
                handles.extend((read.value,write.value))
                resources.rt.require(all(type(n) is int and 0 < n < 2**64 for n in handles) and
                    len(set(handles)) == len(handles), 'Git distinct positive pipe creation handles')
                self.read_handles[name] = read.value
                self.writers[name] = NativePipeWriter(write.value)
                self.checkpoint()
            self.result = True
            return {name:dict(event) for name,event in self.events.items()}
        except BaseException as failure:
            self._failed(failure)

    def bind_spawn(self, sinks):
        publication=getattr(self,'original_publication_resources',None)
        if publication is not None:
            publication._fixed()
            resources.rt.require(not publication.close_started and not publication.unresolved(),
                'closed or unresolved publication pipes cannot be spawned')
        if self.error is not None:
            self._failed(self.error)
        try:
            if self.spawn_io is not None:
                self.rejected_sinks = sinks
                resources.rt.require(False, 'Git pipe spawn IO cannot be rebound')
            self.original_sinks = sinks  # Keep rejected resources before copy/validation.
            self.sinks = dict(sinks) if type(sinks) is dict else sinks
            resources.rt.require(self.result is True and set(self.events) == {'stdout','stderr'},
                                 'Git pipes need original successful creation')
            self.spawn_io = SpawnIOOwner(read_handles=self.read_handles,sinks=self.sinks,writers=self.writers)
            self.spawn_io.pipe_creator = self
            self.spawn_io.native.pipe_creator = self
            self.native.pipe_successor = self.spawn_io.native
            return self.spawn_io
        except BaseException as failure:
            self._failed(failure)


class SpawnIOOwner:
    """Keep caller-owned readers/sinks/writers across opt-in spawn cleanup.

    This creates no pipe and grants no output/recovery/close proof. Even before
    a Job exists, the original exception keeps every supplied IO resource.
    """
    def __init__(self, *, read_handles, sinks, writers):
        self.original_inputs = (read_handles, sinks, writers)
        self.read_handles, self.sinks, self.writers = read_handles, sinks, writers
        self.native = UnreapedJob(None, None, None,
            {'status':'pending','phase':'spawn_io','formal_permission':False})
        self.native.spawn_io_owner = self
        self.entered = False
        self.binding = self.rejected_binding = self.alias_conflict = None
        self.secondary_owner = None
        self.native_write_handles = {}
        self.writer_close_pending = self.writer_close_error = self.writer_close_result = None
        self.writer_close_events = {}
        self.writer_close_checkpoint = None
        self.writer_close_started = False
        try:
            for name in ('read_handles','sinks','writers'):
                value = getattr(self, name)
                if type(value) is dict:
                    setattr(self, name, dict(value))
            for name in ('read_handles','sinks','writers'):
                value = getattr(self, name)
                paths.require(type(value) is dict and set(value) == {'stdout','stderr'},
                              'spawn original IO mapping')
            paths.require(all(type(h) is int and 0 < h < 2**64 for h in self.read_handles.values())
                          and len(set(self.read_handles.values())) == 2,
                          'spawn distinct additional read handles')
            paths.require(len({id(stream) for mapping in (self.sinks,self.writers)
                               for stream in mapping.values()}) == 4,
                          'spawn original separate IO streams')
        except BaseException as error:
            self.native.original_error = error
            raise self.native from error

    def enter(self, kernel, stdin, stdout, stderr):
        binding = (kernel, stdin, stdout, stderr)
        if self.entered:
            self.rejected_binding = binding
            paths.require(False, 'spawn IO owner cannot be rearmed')
        self.binding = binding  # Before import/environment/Job/stdio/native IO.
        self.entered = True
        creator = getattr(self, 'pipe_creator', None)
        if creator is not None:
            resources.rt.require(type(creator) is NativeGitPipes and creator.spawn_io is self and
                creator.kernel is kernel and creator.error is None and
                self.read_handles == creator.read_handles and all(
                    self.writers[name] is creator.writers[name] and
                    self.writers[name].handle == creator.events[name]['write']
                    for name in ('stdout','stderr')), 'spawn original pipe creator/kernel/handles')
        paths.require(stdout is self.writers['stdout'] and stderr is self.writers['stderr'],
                      'spawn uses the original caller write streams')
        if any(type(writer) is NativePipeWriter for writer in self.writers.values()):
            self.native_write_handles = {name:writer.handle for name,writer in self.writers.items()
                                         if type(writer) is NativePipeWriter}
            paths.require(set(self.native_write_handles) == {'stdout','stderr'} and
                          all(type(h) is int and 0 < h < 2**64 for h in self.native_write_handles.values())
                          and len(set(self.native_write_handles.values())) == 2,
                          'spawn original separate raw writer handles')
            self.require_disjoint()

    def require_disjoint(self):
        native = self.native
        core = {native.job, native.process, native.thread, *native.extra_handles.values()}
        reads, writes = set(self.read_handles.values()), set(self.native_write_handles.values())
        conflict = (reads & core) | (writes & core) | (reads & writes)
        if conflict:
            self.alias_conflict = tuple(sorted(conflict))
            paths.require(False, 'spawn readers cannot alias core/inherited handles')

    def close_parent_writers(self, *, checkpoint):
        """Observe raw CloseHandle returns once; never grant IO/core recovery."""
        if self.writer_close_error is not None:
            raise self.native from self.writer_close_error
        if self.writer_close_result is not None:
            return {**self.writer_close_result,
                    'closed_handles':dict(self.writer_close_result['closed_handles'])}
        self.writer_close_checkpoint = checkpoint  # Hold original callback before validation/IO.
        try:
            paths.require(not self.writer_close_started, 'parent writer close cannot be rearmed')
            self.writer_close_started = True
            paths.require(self.entered and self.binding is not None and callable(checkpoint) and
                          set(self.native_write_handles) == {'stdout','stderr'} and
                          all(type(self.writers[name]) is NativePipeWriter and
                              self.writers[name].handle == handle
                              for name,handle in self.native_write_handles.items()),
                          'parent writer close uses original raw handles')
            self.require_disjoint()
            kernel = self.binding[0]
            for name,handle in self.native_write_handles.items():
                self.writer_close_pending = {'name':name,'handle':handle,'writer':self.writers[name],
                                             'kernel':kernel,'return':None}
                checkpoint()
                self.writer_close_pending['return'] = closed = kernel.CloseHandle(handle)
                paths.require(type(closed) in (int,bool), 'parent writer native close return')
                if not closed:
                    self.writer_close_pending['last_error'] = ctypes.get_last_error()
                    raise OSError(self.writer_close_pending['last_error'], 'parent writer CloseHandle')
                self.writer_close_events[name] = {'api':'CloseHandle','handle':handle,'return':int(closed)}
                checkpoint()
            self.writer_close_result = {
                'format':'anomaly-v03-parent-pipe-writes-closed-v1',
                'closed_handles':dict(self.native_write_handles),'formal_permission':False,
                'execution_authenticated':False,'io_released':False,'parent_ack_authorized':False}
            self.writer_close_pending = None
            return {**self.writer_close_result,'closed_handles':dict(self.native_write_handles)}
        except BaseException as error:
            self.writer_close_error = error
            self.native.parent_writer_close_error = error
            if self.native.original_error is None:
                self.native.original_error = error
            raise self.native from error


def _kernel():
    if os.name != 'nt':
        raise OSError('Windows Job fixture only')
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    k.CreateJobObjectW.restype = w.HANDLE
    k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    k.SetInformationJobObject.restype = w.BOOL
    k.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            w.DWORD, ctypes.POINTER(w.DWORD)]
    k.QueryInformationJobObject.restype = w.BOOL
    k.CreateProcessW.argtypes = [w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                 w.BOOL, w.DWORD, ctypes.c_void_p, w.LPCWSTR,
                                 ctypes.POINTER(_StartupInfo),
                                 ctypes.POINTER(_ProcessInformation)]
    k.CreateProcessW.restype = w.BOOL
    k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    k.AssignProcessToJobObject.restype = w.BOOL
    k.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
    k.IsProcessInJob.restype = w.BOOL
    k.ResumeThread.argtypes = [w.HANDLE]
    k.ResumeThread.restype = w.DWORD
    k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    k.WaitForSingleObject.restype = w.DWORD
    k.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
    k.GetExitCodeProcess.restype = w.BOOL
    k.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
    k.TerminateJobObject.restype = w.BOOL
    k.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
    k.TerminateProcess.restype = w.BOOL
    k.CloseHandle.argtypes = [w.HANDLE]
    k.CloseHandle.restype = w.BOOL
    k.GetCurrentProcess.argtypes = []
    k.GetCurrentProcess.restype = w.HANDLE
    k.DuplicateHandle.argtypes = [w.HANDLE, w.HANDLE, w.HANDLE,
                                  ctypes.POINTER(w.HANDLE), w.DWORD,
                                  w.BOOL, w.DWORD]
    k.DuplicateHandle.restype = w.BOOL
    k.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, w.DWORD,
                                                     w.DWORD,
                                                     ctypes.POINTER(ctypes.c_size_t)]
    k.InitializeProcThreadAttributeList.restype = w.BOOL
    k.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, w.DWORD,
                                             ctypes.c_size_t, ctypes.c_void_p,
                                             ctypes.c_size_t, ctypes.c_void_p,
                                             ctypes.c_void_p]
    k.UpdateProcThreadAttribute.restype = w.BOOL
    k.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    k.DeleteProcThreadAttributeList.restype = None
    k.PeekNamedPipe.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD,
                               ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD),
                               ctypes.POINTER(w.DWORD)]
    k.PeekNamedPipe.restype = w.BOOL
    k.WriteFile.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD,
                           ctypes.POINTER(w.DWORD), ctypes.c_void_p]
    k.WriteFile.restype = w.BOOL
    k.ReadFile.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD,
                          ctypes.POINTER(w.DWORD), ctypes.c_void_p]
    k.ReadFile.restype = w.BOOL
    k.CreatePipe.argtypes = [ctypes.POINTER(w.HANDLE),ctypes.POINTER(w.HANDLE),ctypes.c_void_p,w.DWORD]
    k.CreatePipe.restype = w.BOOL
    return k


def _need(ok, label):
    if not ok:
        raise OSError(ctypes.get_last_error(), label)


def _new_job(k):
    job = k.CreateJobObjectW(None, None)  # Unnamed: no other process joins it.
    _need(job, 'CreateJobObjectW')
    try:
        limits = _ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        _need(k.SetInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                                        ctypes.byref(limits), ctypes.sizeof(limits)),
              'SetInformationJobObject')
        observed = _ExtendedLimit()
        _need(k.QueryInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                                          ctypes.byref(observed), ctypes.sizeof(observed),
                                          None), 'QueryInformationJobObject limits')
        flags = observed.BasicLimitInformation.LimitFlags
        _need(flags & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE and
              not flags & (JOB_OBJECT_LIMIT_BREAKAWAY_OK |
                           JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK),
              'Job limits changed')
        return job
    except BaseException as error:
        if not k.CloseHandle(job):
            raise UnclosedHandles({'job': job},
                                  {'status': 'failed', 'phase': 'new_job',
                                   'observation_error_type': type(error).__name__,
                                   'formal_permission': False}) from error
        raise


def _accounting(k, job):
    value = _BasicAccounting()
    _need(k.QueryInformationJobObject(job, JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                                      ctypes.byref(value), ctypes.sizeof(value), None),
          'QueryInformationJobObject accounting')
    return {'total_processes': int(value.TotalProcesses),
            'active_processes': int(value.ActiveProcesses),
            'limit_terminated_processes': int(value.TotalTerminatedProcesses)}


def valid_job_memory(value):
    """Check the bounded native Job peak observation saved in a CLI report."""
    return (type(value) is dict and set(value) == {
        'information_class', 'limit_flags',
        'peak_process_memory_used_bytes', 'peak_job_memory_used_bytes'} and
        value['information_class'] == JOB_OBJECT_EXTENDED_LIMIT_INFORMATION and
        type(value['limit_flags']) is int and
        value['limit_flags'] & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE != 0 and
        value['limit_flags'] & (JOB_OBJECT_LIMIT_BREAKAWAY_OK |
                                JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK |
                                JOB_OBJECT_LIMIT_PROCESS_MEMORY |
                                JOB_OBJECT_LIMIT_JOB_MEMORY) == 0 and
        type(value['peak_process_memory_used_bytes']) is int and
        type(value['peak_job_memory_used_bytes']) is int and
        0 < value['peak_process_memory_used_bytes'] <=
        value['peak_job_memory_used_bytes'] <= ctypes.c_size_t(-1).value)


def _job_memory(k, job):
    value = _ExtendedLimit()
    returned = w.DWORD()
    _need(k.QueryInformationJobObject(
        job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(value),
        ctypes.sizeof(value), ctypes.byref(returned)),
        'QueryInformationJobObject memory')
    _need(returned.value == ctypes.sizeof(value), 'Job memory result length')
    observed = {
        'information_class': JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        'limit_flags': int(value.BasicLimitInformation.LimitFlags),
        'peak_process_memory_used_bytes': int(value.PeakProcessMemoryUsed),
        'peak_job_memory_used_bytes': int(value.PeakJobMemoryUsed),
    }
    _need(valid_job_memory(observed), 'Job memory peaks inconsistent')
    return observed


def _root_exit(k, process):
    result = k.WaitForSingleObject(process, 0)
    if result == WAIT_TIMEOUT:
        return None
    _need(result == WAIT_OBJECT_0, 'WaitForSingleObject root')
    code = w.DWORD()
    _need(k.GetExitCodeProcess(process, ctypes.byref(code)), 'GetExitCodeProcess')
    _need(code.value != STILL_ACTIVE, 'signaled root returned STILL_ACTIVE')
    return int(code.value)


def _wait_empty(k, job, process, deadline):
    """Wait for both empty Job accounting and the owned root process handle."""
    last = None
    while time.monotonic() < deadline:
        last = _accounting(k, job)
        exit_code = _root_exit(k, process)
        if last['active_processes'] == 0 and exit_code is not None:
            return last, exit_code
        time.sleep(0.025)
    last = _accounting(k, job)
    return last, _root_exit(k, process)


def _grandchild_started(evidence_dir, root_pid, accounting):
    """Check two bounded, post-exit fixture markers against Job accounting."""
    if root_pid is None or accounting is None or accounting['total_processes'] < 2:
        return False
    raws = []
    for name in ('parent-started.txt', 'grandchild-started.txt'):
        path = evidence_dir / name
        try:
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_size > 32 or
                    info.st_nlink != 1 or
                    getattr(info, 'st_file_attributes', 0) & 0x400):
                return False
            raws.append(path.read_bytes())
        except OSError:
            return False
    if re.fullmatch(rb'[1-9][0-9]{0,9}:[1-9][0-9]{0,9}', raws[0]) is None or \
            re.fullmatch(rb'[1-9][0-9]{0,9}', raws[1]) is None:
        return False
    parent, child = (int(value) for value in raws[0].split(b':'))
    return parent == root_pid and child == int(raws[1]) and child != root_pid


def run_fixture(evidence_dir, *, mode, wall_seconds=5.0,
                cleanup_seconds=5.0):
    """Run only the invented fixture; no arbitrary CLI or registered input.

    A new Job is configured before the suspended root is assigned and resumed.
    On timeout, a nonzero root exit, or any observation failure, terminate the
    Job and confirm ActiveProcesses==0 before returning a failed report.  If
    that cannot be confirmed, raise with all still-owned handles retained.
    """
    if mode not in ('success', 'timeout', 'parent-fail'):
        raise ValueError('invented Job fixture mode')
    if type(wall_seconds) not in (int, float) or not math.isfinite(wall_seconds) or wall_seconds <= 0:
        raise ValueError('positive finite Job fixture wall seconds')
    if type(cleanup_seconds) not in (int, float) or not math.isfinite(cleanup_seconds) or cleanup_seconds <= 0:
        raise ValueError('positive finite Job fixture cleanup seconds')
    evidence_dir = Path(evidence_dir).resolve(strict=True)
    if not evidence_dir.is_dir() or any(evidence_dir.iterdir()):
        raise ValueError('empty invented evidence directory required')
    if not FIXTURE.is_file():
        raise FileNotFoundError(FIXTURE)
    before = runtime.probe_runtime(ROOT)
    k = _kernel()
    job = _new_job(k)
    process = thread = None
    started = time.monotonic()
    root_pid = None
    root_resumed = assigned = False
    exit_code = None
    reason = None
    observation_error = None
    accounting = None
    try:
        args = [sys.executable, '-B', str(FIXTURE), 'parent', mode,
                str(evidence_dir)]
        startup = _StartupInfo()
        startup.cb = ctypes.sizeof(startup)
        created = _ProcessInformation()
        command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
        _need(k.CreateProcessW(sys.executable, command_line, None, None,
                               False, CREATE_SUSPENDED | CREATE_NO_WINDOW,
                               None, str(ROOT), ctypes.byref(startup),
                               ctypes.byref(created)), 'CreateProcessW')
        process, thread, root_pid = created.hProcess, created.hThread, int(created.dwProcessId)
        _need(k.AssignProcessToJobObject(job, process), 'AssignProcessToJobObject')
        member = w.BOOL()
        _need(k.IsProcessInJob(process, job, ctypes.byref(member)) and member.value,
              'IsProcessInJob')
        assigned = True
        _need(k.ResumeThread(thread) == 1, 'ResumeThread')
        root_resumed = True
        while True:
            accounting = _accounting(k, job)
            exit_code = _root_exit(k, process)
            if exit_code is not None and exit_code != 0:
                reason = 'root_exit_nonzero'
                break
            if accounting['active_processes'] == 0:
                break
            if time.monotonic() - started >= wall_seconds:
                reason = 'wall_limit'
                break
            time.sleep(0.025)
        if reason is None:
            after = runtime.probe_runtime(ROOT)
            if after != before:
                reason = 'runtime_changed'
        if reason is not None:
            _need(k.TerminateJobObject(job, 0xE001), 'TerminateJobObject')
    except BaseException as error:
        reason = reason or 'observation_error'
        observation_error = type(error).__name__
        if process is not None:
            try:
                if assigned:
                    _need(k.TerminateJobObject(job, 0xE002), 'TerminateJobObject after error')
                else:
                    _need(k.TerminateProcess(process, 0xE003), 'TerminateProcess suspended root')
            except BaseException as stop_error:
                observation_error += ':' + type(stop_error).__name__
    finally:
        if process is not None:
            try:
                if assigned:
                    accounting, exit_code = _wait_empty(
                        k, job, process, time.monotonic() + cleanup_seconds)
                else:
                    wait = k.WaitForSingleObject(process, int(cleanup_seconds * 1000))
                    if wait == WAIT_OBJECT_0:
                        exit_code = _root_exit(k, process)
                    accounting = _accounting(k, job)
            except BaseException as error:
                observation_error = (observation_error + ':' if observation_error else '') + type(error).__name__
    elapsed = time.monotonic() - started
    confirmed = (process is None or
                 (exit_code is not None and accounting is not None and
                  accounting['active_processes'] == 0))
    tree_exit_confirmed = (assigned and exit_code is not None and
                           accounting is not None and
                           accounting['active_processes'] == 0)
    grandchild_started = (_grandchild_started(evidence_dir, root_pid, accounting)
                          if tree_exit_confirmed else False)
    if tree_exit_confirmed and exit_code == 0 and reason is None and not grandchild_started:
        reason = 'grandchild_start_unconfirmed'
    report = {'format': 'anomaly-v03-preformal-job-tree-owner-v1',
              'scope': 'invented-26h2-job-fixture-only',
              'mode': mode, 'status': 'complete' if
              (tree_exit_confirmed and root_resumed and grandchild_started and
               exit_code == 0 and
               reason is None and observation_error is None) else 'failed',
              'root_pid': root_pid, 'root_resumed': root_resumed,
              'job_assignment_confirmed': assigned,
              'root_exit_code': exit_code,
              'job_accounting': accounting,
              'job_all_assigned_processes_exit_confirmed': tree_exit_confirmed,
              'grandchild_started_confirmed': grandchild_started,
              'individual_descendant_exit_codes_authenticated': False,
              'stop_reason': reason, 'observation_error_type': observation_error,
              'elapsed_seconds': elapsed,
              'formal_permission': False, 'registered_data_read': False,
              'campaign_evaluations_credited': 0}
    if not confirmed:
        raise UnreapedJob(job, process, thread, report)
    unclosed = {}
    for name, handle in (('thread', thread), ('process', process), ('job', job)):
        if handle is not None:
            if not k.CloseHandle(handle):
                unclosed[name] = handle
    if unclosed:
        report['status'] = 'failed'
        report['observation_error_type'] = 'CloseHandle'
        report['unclosed_handles'] = sorted(unclosed)
        raise UnclosedHandles(unclosed, report)
    return report


def _close_owned(k, job, process, thread, report):
    handles = {name:handle for name,handle in
               (('thread',thread),('process',process),('job',job)) if handle is not None}
    return _close_handles(k, handles, report)


def _close_handles(k, handles, report):
    """Keep every named original, including inherited handles, before close."""
    handles = dict(handles)
    retained = UnclosedHandles(handles, report)  # Own everything before CloseHandle or diagnostics.

    def failed():
        try:
            report['status'] = 'failed'
            report['stop_reason'] = 'handle_close'
            report['observation_errors'] = [*report.get('observation_errors', []),
                                            {'stage': 'handle_close', 'error_type': 'OSError'}]
            report['unclosed_handles'] = sorted(retained.handles)
        except BaseException as diagnostic:
            retained.diagnostic_error = diagnostic

    for name, handle in handles.items():
        try:
            closed = k.CloseHandle(handle)
        except BaseException as error:
            # Preserve the failed/unknown handle and all unattempted handles.
            # Do not continue closing or discard the owner on an interruption.
            retained.close_error = error
            failed()
            raise retained from error
        if closed:
            retained.handles.pop(name)
    if retained.handles:
        failed()
        raise retained
    return {'format':'anomaly-v03-owned-handles-closed-v1', 'closed_handles':handles}


def _reap_partial_spawn(k, job, created, assigned, extra_handles):
    if created.hProcess:
        try:
            if assigned:
                _need(k.TerminateJobObject(job, 0xE004),
                      'TerminateJobObject failed spawn')
            else:
                _need(k.TerminateProcess(created.hProcess, 0xE005),
                      'TerminateProcess failed spawn')
            accounting, exit_code = _wait_empty(
                k, job, created.hProcess, time.monotonic() + 30)
            _need(accounting['active_processes'] == 0 and
                  exit_code is not None, 'failed spawn Job empty')
        except BaseException as error:
            raise UnreapedJob(job, created.hProcess, created.hThread,
                              {'status': 'failed', 'phase': 'spawn',
                               'assignment_confirmed': assigned,
                               'formal_permission': False},
                              extra_handles=extra_handles) from error
    try:
        _close_owned(k, job, created.hProcess or None, created.hThread or None,
                     {'status': 'failed', 'phase': 'spawn',
                      'formal_permission': False})
    except UnclosedHandles as error:
        error.handles.update(extra_handles)
        raise


def _environment_block(environment):
    paths.require(type(environment) is dict and environment and
                  all(type(key) is str and key and '=' not in key and
                      type(value) is str and '\x00' not in key + value
                      for key, value in environment.items()) and
                  len({key.casefold() for key in environment}) == len(environment),
                  'explicit Windows environment')
    text = ''.join(
        key + '=' + environment[key] + '\x00'
        for key in sorted(environment, key=str.casefold)) + '\x00'
    return ctypes.create_unicode_buffer(text, len(text))


def _spawn_cli(k, argv, cwd, stdin, stdout, stderr, *, environment=None, spawn_io=None):
    if spawn_io is None:
        return _spawn_cli_inner(k, argv, cwd, stdin, stdout, stderr, environment=environment)
    # Keep all entry inputs even when the opt-in descriptor is rejected.
    rejected = UnreapedJob(None, None, None,
        {'status':'failed','phase':'spawn_io_entry','formal_permission':False})
    rejected.spawn_io_inputs = (spawn_io, k, stdin, stdout, stderr)
    retained = rejected
    try:
        paths.require(type(spawn_io) is SpawnIOOwner, 'spawn original IO owner required')
        retained = spawn_io.native
        spawn_io.enter(k, stdin, stdout, stderr)
        return _spawn_cli_inner(k, argv, cwd, stdin, stdout, stderr,
                                environment=environment, held_io=spawn_io)
    except BaseException as error:
        if isinstance(error, (UnreapedJob, UnclosedHandles)) and error is not retained:
            # _new_job/cleanup may already own a different exact native exception.
            error.spawn_io_owner = spawn_io
            if type(spawn_io) is SpawnIOOwner:
                spawn_io.secondary_owner = error
            raise
        if error is retained:
            raise
        if retained.original_error is None:
            retained.original_error = error
        raise retained from error


def _spawn_cli_inner(k, argv, cwd, stdin, stdout, stderr, *, environment=None, held_io=None):
    """Create suspended, assign to a non-breakaway Job, then return handles.

    Only the three duplicated standard handles are inherited. The caller owns
    the suspended root and must resume or terminate it before closing handles.
    """
    import msvcrt

    block = None if environment is None else _environment_block(environment)
    if held_io is not None:
        held_io.native.environment_block = block
    job = _new_job(k)
    if held_io is not None:
        held_io.native.job = job
    created = _ProcessInformation()
    if held_io is not None:
        held_io.native.created_process_info = created
    inherited = []
    if held_io is not None:
        held_io.native.inherited_snapshot = inherited
    attributes = None
    attributes_ready = False
    assigned = False
    result = spawn_error = None
    try:
        if held_io is not None:
            held_io.require_disjoint()
        self_handle = k.GetCurrentProcess()
        for index, stream in enumerate((stdin, stdout, stderr)):
            duplicate = w.HANDLE()
            if held_io is not None:
                held_io.native.pending_duplicate = duplicate
            if held_io is not None and index > 0 and type(stream) is NativePipeWriter:
                source = held_io.native_write_handles[
                    'stdout' if index == 1 else 'stderr']
                paths.require(stream.handle == source, 'spawn raw writer handle cannot change')
            else:
                source = msvcrt.get_osfhandle(stream.fileno())
            _need(k.DuplicateHandle(self_handle, source,
                                    self_handle, ctypes.byref(duplicate), 0, True,
                                    DUPLICATE_SAME_ACCESS), 'DuplicateHandle stdio')
            inherited.append(duplicate.value)
            if held_io is not None:
                held_io.native.extra_handles = {'inherited_'+str(i):h for i,h in enumerate(inherited)}
                held_io.native.pending_duplicate = None
                held_io.require_disjoint()
        size = ctypes.c_size_t()
        k.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        _need(size.value > 0, 'InitializeProcThreadAttributeList sizing')
        attributes = ctypes.create_string_buffer(size.value)
        if held_io is not None:
            held_io.native.attributes = attributes
        _need(k.InitializeProcThreadAttributeList(attributes, 1, 0,
                                                  ctypes.byref(size)),
              'InitializeProcThreadAttributeList')
        attributes_ready = True
        handles = (w.HANDLE * len(inherited))(*inherited)
        _need(k.UpdateProcThreadAttribute(
            attributes, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            ctypes.cast(handles, ctypes.c_void_p), ctypes.sizeof(handles),
            None, None), 'UpdateProcThreadAttribute handle list')
        startup = _StartupInfoEx()
        startup.StartupInfo.cb = ctypes.sizeof(startup)
        startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES
        startup.StartupInfo.hStdInput = inherited[0]
        startup.StartupInfo.hStdOutput = inherited[1]
        startup.StartupInfo.hStdError = inherited[2]
        startup.lpAttributeList = ctypes.cast(attributes, ctypes.c_void_p)
        command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
        _need(k.CreateProcessW(argv[0], command_line, None, None, True,
                               CREATE_SUSPENDED | CREATE_NO_WINDOW |
                               EXTENDED_STARTUPINFO_PRESENT |
                               (CREATE_UNICODE_ENVIRONMENT if block is not None else 0),
                               None if block is None else ctypes.cast(block, ctypes.c_void_p), str(cwd),
                               ctypes.cast(ctypes.byref(startup),
                                           ctypes.POINTER(_StartupInfo)),
                               ctypes.byref(created)), 'CreateProcessW')
        if held_io is not None:
            held_io.native.process, held_io.native.thread = created.hProcess, created.hThread
            held_io.require_disjoint()
        _need(k.AssignProcessToJobObject(job, created.hProcess),
              'AssignProcessToJobObject')
        member = w.BOOL()
        _need(k.IsProcessInJob(created.hProcess, job, ctypes.byref(member))
              and member.value, 'IsProcessInJob')
        assigned = True
        result = job, created.hProcess, created.hThread, int(created.dwProcessId)
    except BaseException as error:
        spawn_error = error
    finally:
        retained = (held_io.native if held_io is not None else UnreapedJob(
            job, created.hProcess or None, created.hThread or None,
            {'status':'failed','phase':'spawn_cleanup','assignment_confirmed':assigned,
             'formal_permission':False},
            extra_handles={'inherited_'+str(index):handle for index,handle in enumerate(inherited)}))
        if held_io is not None:
            retained.job, retained.process, retained.thread = job, created.hProcess or None, created.hThread or None
            retained.report = {'status':'failed','phase':'spawn_cleanup',
                               'assignment_confirmed':assigned,'formal_permission':False}
            retained.extra_handles = {'inherited_'+str(i):h for i,h in enumerate(inherited)}
        retained.original_error = spawn_error
        retained.attributes = attributes  # Keep its Python buffer alive before Delete/diagnostics.
        retained.attribute_list_cleanup_pending = attributes_ready
        if held_io is not None and held_io.alias_conflict is not None:
            raise retained from spawn_error  # Never close an aliased read handle as stdio.
        if attributes_ready:
            try:
                k.DeleteProcThreadAttributeList(attributes)
                retained.attribute_list_cleanup_pending = False
            except BaseException as error:
                retained.cleanup_error = error
                raise retained from error
        # These are parent-side duplicates only. The child inherited its own
        # copies at CreateProcessW and can keep writing after these close.
        stdio_owner = None
        try:
            stdio_event = _close_handles(k, retained.extra_handles,
                {'status':'failed','phase':'spawn_stdio_close','formal_permission':False})
            unclosed_stdio = {}
            if held_io is not None:
                retained.stdio_close_event = stdio_event
                retained.extra_handles = {}
        except UnclosedHandles as error:
            retained.cleanup_error = stdio_owner = error
            retained.extra_handles = dict(error.handles)
            unclosed_stdio = dict(error.handles)
            if error.close_error is not None:
                retained.unknown_close_handles = tuple(error.handles)
                raise retained from error
    if spawn_error is not None or unclosed_stdio:
        if held_io is not None:
            # Preserve this exact core + additional IO. The opt-in keeper must
            # stop/reap before a separate verified IO/core close handoff.
            raise retained from (spawn_error if spawn_error is not None else stdio_owner)
        _reap_partial_spawn(k, job, created, assigned, unclosed_stdio)
        if unclosed_stdio:
            raise stdio_owner from spawn_error
        raise spawn_error
    return result


def supervise_cli(argv, cwd, control_root, limits, *, runtime_probe,
                  boundary, on_started, stdout_name='report.json',
                  cleanup_seconds=30.0):
    """Supervise one externally pinned invented CLI and all Job members.

    The caller validates argv/source and saves this report. A successful
    report requires a zero root exit, empty Job accounting, matching runtime,
    and bounded direct CLI observations. Native Job memory peaks are observed,
    while descendant exit codes and a shared tree budget remain unauthenticated.
    """
    direct_supervisor._limits(limits)
    paths.require(type(argv) is list and argv and
                  all(type(x) is str and x for x in argv), 'Job CLI argv')
    paths.require(stdout_name in ('report.json', 'stdout.jsonl'),
                  'Job CLI stdout name')
    paths.require(type(cleanup_seconds) in (int, float) and
                  math.isfinite(cleanup_seconds) and cleanup_seconds > 0,
                  'Job cleanup seconds')
    cwd = paths.regular_path(Path(cwd), directory=True)
    control = Path(control_root).absolute()
    paths.regular_path(control.parent, directory=True)
    paths.regular_path(control, directory=True, missing=True)
    control.mkdir()
    stdout_path, stderr_path = control / stdout_name, control / 'stderr.json'
    k = _kernel()
    job = process = thread = None
    pid = exit_code = accounting = job_memory = None
    before = after = free_before = free_after = None
    errors, peak, reason = [], 0, None
    started = time.monotonic()
    resumed = assigned = False

    def error(stage, value):
        errors.append({'stage': stage, 'error_type': type(value).__name__})

    def sample_memory():
        nonlocal peak
        peak = max(peak, resources.memory_bytes(process)['peak_private_bytes'])

    def budget():
        if time.monotonic() - started > limits['wall_seconds']:
            return 'time_limit'
        if peak > limits['private_bytes']:
            return 'memory_limit'
        total = sum(path.stat().st_size for path in (stdout_path, stderr_path)
                    if path.exists())
        return 'output_limit' if total > limits['output_bytes'] else None

    try:
        before = runtime_probe()
        direct_supervisor.policy.validate_runtime(before)
        free_before = resources.require_start_resources(cwd)
        boundary()
        reason = budget()
        if reason is None:
            with open(os.devnull, 'rb') as stdin, \
                    stdout_path.open('xb') as stdout, \
                    stderr_path.open('xb') as stderr:
                job, process, thread, pid = _spawn_cli(
                    k, argv, cwd, stdin, stdout, stderr)
                assigned = True
                on_started(type('OwnedCli', (), {'pid': pid,
                                                  '_handle': process})())
                _need(k.ResumeThread(thread) == 1, 'ResumeThread CLI')
                resumed = True
                while True:
                    accounting = _accounting(k, job)
                    exit_code = _root_exit(k, process)
                    if exit_code is not None and exit_code != 0:
                        reason = 'root_exit_nonzero'
                        break
                    if accounting['active_processes'] == 0 and exit_code is not None:
                        break
                    if exit_code is None:
                        sample_memory()
                    reason = budget()
                    if reason is not None:
                        break
                    time.sleep(0.25)
    except resources.ResourceStop as value:
        reason = value.reason
    except KeyboardInterrupt:
        reason = 'interrupted'
    except (UnreapedJob, UnclosedHandles):
        # _spawn_cli still owns native handles in these cases. Returning a
        # terminal report would discard the only reconciliation handle.
        raise
    except Exception as value:
        error('supervision', value)
        reason = reason or 'observation_error'
    finally:
        if process is not None:
            try:
                accounting = _accounting(k, job)
                exit_code = _root_exit(k, process)
                if reason is not None or exit_code is None or \
                        accounting['active_processes'] != 0:
                    # A success-path child may outlive the root. Give it only
                    # the remaining wall budget, then terminate the Job.
                    if reason is None and exit_code == 0:
                        accounting, exit_code = _wait_empty(
                            k, job, process, started + limits['wall_seconds'])
                    if reason is not None or exit_code is None or \
                            accounting['active_processes'] != 0:
                        reason = reason or 'time_limit'
                        _need(k.TerminateJobObject(job, 0xE006),
                              'TerminateJobObject CLI')
                accounting, exit_code = _wait_empty(
                    k, job, process, time.monotonic() + cleanup_seconds)
                if accounting['active_processes'] != 0 or exit_code is None:
                    raise UnreapedJob(job, process, thread, {
                        'status': 'failed', 'phase': 'reap',
                        'root_pid': pid, 'root_exit_code': exit_code,
                        'job_accounting': accounting,
                        'formal_permission': False})
            except UnreapedJob:
                raise
            except BaseException as value:
                error('job_reap', value)
                raise UnreapedJob(job, process, thread, {
                    'status': 'failed', 'phase': 'reap',
                    'root_pid': pid, 'root_exit_code': exit_code,
                    'job_accounting': accounting,
                    'formal_permission': False}) from value
            try:
                sample_memory()
            except BaseException as value:
                error('final_worker_memory', value)
            try:
                job_memory = _job_memory(k, job)
            except BaseException as value:
                error('final_job_memory', value)
        try:
            after = runtime_probe()
            direct_supervisor.policy.validate_runtime(after)
            if before is not None and after != before:
                reason = 'runtime_changed'
            free_after = resources.free_resources(cwd)
            boundary()
        except resources.ResourceStop as value:
            reason = reason or value.reason
        except BaseException as value:
            error('final_context', value)
            reason = reason or 'observation_error'
    output = stderr = None
    try:
        limit_reason = budget()
        reason = reason or limit_reason
        if limit_reason != 'output_limit':
            output = direct_supervisor._file_pin(stdout_path, limits['output_bytes'])
            remaining = limits['output_bytes'] - (output['bytes'] if output else 0)
            stderr = direct_supervisor._file_pin(stderr_path, remaining)
    except resources.ResourceStop as value:
        reason = value.reason
    except BaseException as value:
        error('output_observation', value)
    job_confirmed = (assigned and accounting is not None and
                     accounting['active_processes'] == 0 and exit_code is not None)
    complete = (job_confirmed and resumed and exit_code == 0 and
                reason is None and not errors and job_memory is not None and
                before is not None and
                after == before)
    report = {
        'format': 'anomaly-v03-owned-process-monitor-v1',
        'argv': list(argv), 'limits': dict(limits),
        'status': 'complete' if complete else 'failed',
        'exit_code': exit_code, 'worker_pid': pid,
        'worker_started': process is not None,
        'worker_exit_confirmed': exit_code is not None,
        'stop_reason': reason,
        'elapsed_seconds': time.monotonic() - started,
        'peak_worker_private_bytes': peak,
        'observation_errors': errors,
        'output': output, 'stderr': stderr,
        'runtime_before': before, 'runtime_after': after,
        'free_before': free_before, 'free_after': free_after,
        'job': {'format': 'anomaly-v03-preformal-owned-cli-job-v1',
                'assignment_confirmed': assigned,
                'root_resumed': resumed,
                'accounting': accounting,
                'memory': job_memory,
                'all_assigned_processes_exit_confirmed': job_confirmed,
                'individual_descendant_exit_codes_authenticated': False,
                'whole_tree_resource_budget_measured': False},
        'formal_permission': False, 'performance_status': 'not_evaluated',
    }
    _close_owned(k, job, process, thread, report)
    return report
