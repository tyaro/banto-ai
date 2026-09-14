"""Held driver with real collector/ownership objects and fake native surfaces."""
import ctypes as C
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_held_driver as drv
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures.anomaly_v03_tracked_open import TrackedOpen
from tests import test_anomaly_v03_held_consumer as consumer
from tests import test_anomaly_v03_observed_evidence as observed
from tests import test_anomaly_v03_sealed_files as sealing


def fail(error):
    def operation(*args, **kwargs):
        raise error
    return operation


class Context(drv.WindowsHeldContext):
    def __init__(self):
        super().__init__(Path.cwd() / "fake-held-unused", "a" * 40)
        self.events, self.hooks, self.saved = [], {}, []
        (self.reader, self.api, self.table, self.original, self.group,
         self.backend, self.generation) = consumer.setup()
        self._source_root = self.original[0]
        ancestors = [self.lease(h) for h in (601, 602, 701, 702)]
        self.source._leases = ancestors[:2] + list(self.original)
        self.sink._leases = ancestors[2:]
        self.source._started = self.source._connected = True
        self.sink._started = self.sink._connected = True

    def lease(self, handle):
        self.table.live[handle] = "original"
        lease = TrackedOpen(self.table)
        lease.acquire(lambda cell: setattr(cell, "handle", handle), lambda h: object())
        return lease

    def hit(self, name):
        self.events.append(name)
        if name in self.hooks:
            return self.hooks[name]()

    def connect(self):
        return self.hit("connect")

    def prepare(self, guard):
        self.reader._external_guard = guard
        self.hit("prepare")
        guard()
        self._prepared = True

    def guard(self):
        return self.hit("guard")

    def persist_collection(self, state):
        self.saved.append(json.loads(json.dumps(state)))
        return self.hit("persist")

    def close_children(self, *, primary=None):
        self.hit("children")
        return super().close_children(primary=primary)

    def close_root(self, *, primary=None):
        self.hit("root")
        return super().close_root(primary=primary)

    def close_ancestors(self, *, primary=None):
        self.hit("ancestors")
        return super().close_ancestors(primary=primary)


class DriverTests(unittest.TestCase):
    def test_collection_persist_root_ancestors_order_and_closed_payload_gate(self):
        ctx = Context()
        driver = drv.HeldDriver(ctx)
        ctx.hooks["persist"] = lambda: self.assertEqual(set(ctx.table.live), {101,601,602,701,702})
        ctx.table.hooks[101] = lambda: self.assertTrue({601,602,701,702}.issubset(ctx.table.live))
        driver.run()
        self.assertEqual(driver.exit_code(), 0)
        self.assertFalse(ctx.table.live)
        self.assertLess(ctx.events.index("persist"), ctx.events.index("root"))
        self.assertLess(ctx.events.index("root"), ctx.events.index("ancestors"))
        report = json.loads(driver.report_bytes())
        self.assertEqual(report["held_driver"], "complete")
        self.assertFalse(report["consumer_payload_released"])
        self.assertEqual(report["namespace_consistency"], "unresolved")
        self.assertNotIn("bytes_b64", driver.report_bytes().decode())
        with self.assertRaises(owned.OwnershipError): ctx.reader.consumer_payload()

    def test_unknown_child_close_retains_root_and_all_ancestors_without_retry(self):
        ctx = Context()
        error = ValueError("child close unknown")
        ctx.table.hooks[404] = fail(error)
        driver = drv.HeldDriver(ctx)
        for operation in (driver.run, driver.finish, driver.finish):
            with self.assertRaises(ValueError) as caught: operation()
            self.assertIs(caught.exception, error)
        self.assertEqual(driver.exit_code(), 81)
        self.assertEqual(set(ctx.table.live), {101,404,601,602,701,702})
        self.assertNotIn("root", ctx.events)
        self.assertNotIn("persist", ctx.events)
        self.assertEqual(ctx.table.calls.count(("close",404)), 1)

    def test_unknown_root_close_retains_ancestors(self):
        ctx = Context()
        ctx.table.hooks[101] = fail(ValueError("root close"))
        driver = drv.HeldDriver(ctx)
        with self.assertRaises(ValueError): driver.run()
        self.assertEqual(driver.exit_code(),81)
        self.assertNotIn("ancestors",ctx.events)
        self.assertEqual(set(ctx.table.live),{101,601,602,701,702})

    def test_ancestor_close_failure_stops_before_its_parent_or_other_sink(self):
        ctx=Context()
        ctx.table.hooks[602]=fail(ValueError("ancestor close"))
        driver=drv.HeldDriver(ctx)
        with self.assertRaises(ValueError): driver.run()
        self.assertEqual(driver.exit_code(),81)
        self.assertEqual(set(ctx.table.live),{601,602,701,702})
        self.assertNotIn(("close",601),ctx.table.calls)

    def test_lifetime_query_failure_is_conservative_and_preserves_primary(self):
        for query, absent in (("children_require_exit","root"),("root_requires_exit","ancestors"),
                              ("requires_exit",None)):
            for secondary in (ValueError("query"), MemoryError("query")):
                ctx=Context()
                primary=RuntimeError("persist")
                ctx.hooks["persist"]=fail(primary)
                setattr(ctx,query,fail(secondary))
                driver=drv.HeldDriver(ctx)
                with self.assertRaises(RuntimeError) as caught: driver.run()
                self.assertIs(caught.exception,primary)
                self.assertEqual(driver.exit_code(),80 if isinstance(secondary,MemoryError) else 81)
                if absent: self.assertNotIn(absent,ctx.events)

    def test_status_failure_cannot_hide_primary_or_trigger_more_work(self):
        ctx=Context()
        primary=ValueError("persist")
        def persist():
            ctx.status=fail(MemoryError("status"))
            raise primary
        ctx.hooks["persist"]=persist
        driver=drv.HeldDriver(ctx)
        with self.assertRaises(ValueError) as caught: driver.run()
        self.assertIs(caught.exception,primary)
        self.assertEqual(driver.exit_code(),80)
        self.assertFalse(ctx.table.live)

    def test_final_guard_silent_stop_is_not_success(self):
        for resource in (False, True):
            ctx=Context()
            primary=ValueError("silent stop")
            def guard():
                if ctx.saved:
                    ctx._record(primary)
                    ctx._resource=resource
            ctx.hooks["guard"]=guard
            driver=drv.HeldDriver(ctx)
            with self.assertRaises(ValueError) as caught: driver.run()
            self.assertIs(caught.exception,primary)
            self.assertEqual(driver.exit_code(),80 if resource else 1)
            self.assertEqual(driver._evidence,"pending")

    def test_read_failure_and_later_root_resource_failure_keep_read_primary(self):
        ctx=Context()
        primary=ValueError("read")
        ctx.api.hooks["read"]=fail(primary)
        ctx.table.hooks[101]=fail(MemoryError("close"))
        driver=drv.HeldDriver(ctx)
        with self.assertRaises(ValueError) as caught: driver.run()
        self.assertIs(caught.exception,primary)
        self.assertEqual(driver.exit_code(),80)
        self.assertTrue(driver._retained)
        self.assertNotIn("persist",ctx.events)
        with self.assertRaises(ValueError): driver.report_bytes()

    def test_swallowed_reentry_at_work_and_teardown_boundaries_latches_stop(self):
        for boundary in ("connect","prepare","guard","persist","children","root","ancestors"):
            for method in ("run","finish"):
                ctx=Context()
                driver=drv.HeldDriver(ctx)
                def reenter():
                    try: getattr(driver,method)()
                    except owned.OwnershipError: pass
                ctx.hooks[boundary]=reenter
                with self.subTest(boundary=boundary,method=method),self.assertRaises(owned.OwnershipError):
                    driver.run()
                self.assertNotEqual(driver.exit_code(),0)
                for handle in (101,404,505,601,602,701,702):
                    self.assertLessEqual(ctx.table.calls.count(("close",handle)),1)

    def test_bad_callback_responses_cannot_succeed(self):
        for method in ("connect","prepare","guard","persist_collection","close_children","close_root","close_ancestors"):
            ctx=Context()
            original=getattr(ctx,method)
            def wrong(*args,**kwargs):
                original(*args,**kwargs)
                return True
            setattr(ctx,method,wrong)
            driver=drv.HeldDriver(ctx)
            with self.subTest(method=method),self.assertRaises(owned.OwnershipError): driver.run()
            self.assertNotEqual(driver.exit_code(),0)

    def test_invalid_lifetime_response_retains_and_invalid_status_stops(self):
        ctx=Context()
        ctx.children_require_exit=lambda:1
        driver=drv.HeldDriver(ctx)
        with self.assertRaises(owned.OwnershipError): driver.run()
        self.assertEqual(driver.exit_code(),81)
        self.assertNotIn("root",ctx.events)
        ctx=Context()
        ctx.status=lambda:(None,1)
        driver=drv.HeldDriver(ctx)
        with self.assertRaises(owned.OwnershipError): driver.run()
        self.assertNotIn("connect",ctx.events)

    def test_resource_before_start_does_no_connection_or_reads(self):
        ctx=Context()
        ctx._resource=True
        driver=drv.HeldDriver(ctx)
        with self.assertRaises(MemoryError): driver.run()
        self.assertEqual(driver.exit_code(),80)
        self.assertNotIn("connect",ctx.events)
        self.assertFalse(ctx.api.calls)

    def test_finished_driver_never_restarts_or_repeats_close(self):
        ctx=Context()
        driver=drv.HeldDriver(ctx)
        driver.finish()
        calls=ctx.table.calls[:]
        driver.finish()
        with self.assertRaises(owned.OwnershipError): driver.run()
        self.assertEqual(ctx.table.calls,calls)
        self.assertEqual(driver.exit_code(),1)

    def test_reporting_fault_changes_exit_without_io_or_primary_replacement(self):
        for error in (MemoryError("report"), ValueError("report")):
            ctx=Context()
            driver=drv.HeldDriver(ctx)
            driver.run()
            calls=ctx.table.calls[:]
            ctx.snapshot=fail(error)
            with self.assertRaises(type(error)) as caught: driver.report_bytes()
            self.assertIs(caught.exception,error)
            self.assertEqual(driver.exit_code(),80 if isinstance(error,MemoryError) else 1)
            self.assertEqual(ctx.table.calls,calls)

    def test_report_size_budget_and_cached_exit_no_callback(self):
        ctx=Context()
        driver=drv.HeldDriver(ctx)
        driver.run()
        ctx.status=ctx.requires_exit=fail(AssertionError("unexpected query"))
        self.assertEqual(driver.exit_code(),0)
        ctx.status=lambda:(None,False)
        driver.MAX_REPORT_BYTES=1
        with self.assertRaises(MemoryError): driver.report_bytes()
        self.assertEqual(driver.exit_code(),80)

    def test_report_callback_reentry_or_silent_stop_cannot_emit_stale_success(self):
        for action in ("run","finish","report_bytes","silent_stop"):
            ctx=Context()
            driver=drv.HeldDriver(ctx)
            driver.run()
            original=ctx.snapshot
            def snapshot():
                if action=="silent_stop": ctx._record(ValueError("report stop"))
                else:
                    try: getattr(driver,action)()
                    except owned.OwnershipError: pass
                return original()
            ctx.snapshot=snapshot
            with self.assertRaises((ValueError,owned.OwnershipError)): driver.report_bytes()
            self.assertEqual(driver.exit_code(),1)


class ContextTests(unittest.TestCase):
    def test_generation_resource_is_visible_even_when_reader_construction_failed(self):
        ctx=Context()
        ctx.reader=None
        primary=ValueError("construction")
        ctx._record(primary)
        ctx.generation._resource=True
        error,resource=ctx.status()
        self.assertIs(error,primary)
        self.assertTrue(resource)

    def test_bootstrap_failure_or_unknown_token_keeps_ancestors(self):
        for target in ("source","sink"):
            for kind in ("bootstrap","token","descriptor"):
                ctx=Context()
                if kind=="bootstrap": getattr(ctx,target)._connected=False
                elif kind=="token":
                    getattr(ctx,target)._token=SimpleNamespace(state="unknown",close_state="unknown")
                else: ctx._parent_sd_state="free_unknown"
                self.assertTrue(ctx.children_require_exit())

    def test_deferred_sink_finish_never_closes_on_bootstrap_failure(self):
        sink=drv.RetainedSink()
        calls=[]
        sink._leases=[SimpleNamespace(close=lambda:calls.append(1))]
        primary=ValueError("bootstrap")
        with self.assertRaises(ValueError) as caught: sink.finish(primary=primary)
        self.assertIs(caught.exception,primary)
        sink.finish()
        self.assertFalse(calls)

    def test_unreleased_adopted_writer_retains_entire_tree(self):
        ctx=Context()
        ctx.original[1].state="ready"
        ctx.original[1].close_state="not_started"
        ctx.table.live[202]="original"
        ctx.close_children(primary=ValueError("prepare"))
        self.assertTrue(ctx.children_require_exit())
        self.assertEqual(ctx.original[0].close_state,"not_started")
        self.assertNotIn(("close",202),ctx.table.calls)

    def test_unadopted_children_close_first_and_stop_on_unknown(self):
        ctx=Context()
        ctx.group.active=False
        ctx.generation=ctx.reader=None
        for lease in ctx.original: lease._custodian=None
        extra=ctx.lease(808)
        ctx.source._leases.append(extra)
        ctx.table.hooks[808]=fail(ValueError("child"))
        ctx.close_children()
        self.assertTrue(ctx.children_require_exit())
        self.assertEqual(ctx.original[0].close_state,"not_started")

    def test_collection_persistence_contains_hash_metadata_and_does_not_advance_journal(self):
        ctx=Context()
        ctx.reader.run()
        before=ctx.group.owner._journal.snapshot()
        values=[]
        ctx.sink.persist_evidence=lambda *args:values.append(args)
        drv.WindowsHeldContext.persist_collection(ctx,ctx.reader.snapshot())
        self.assertEqual(values[0][0],"seal_payload")
        self.assertEqual(hashlib.sha256(values[0][1]).hexdigest(),values[0][2])
        self.assertEqual(before,ctx.group.owner._journal.snapshot())
        self.assertNotIn(b'bytes_b64',values[0][1])

    def test_guard_uses_ancestor_check_and_rejects_journal_stop(self):
        ctx=Context()
        calls=[]
        with patch.object(drv.acquisition.WindowsAcquisitionContext,"guard",side_effect=lambda:calls.append(1)):
            drv.WindowsHeldContext.guard(ctx)
            ctx.group.owner._journal.stop(resource=True)
            with self.assertRaises(MemoryError): drv.WindowsHeldContext.guard(ctx)
        self.assertEqual(calls,[1,1])
        self.assertTrue(ctx.status()[1])


class BootstrapTests(unittest.TestCase):
    def setup_context(self, *, persist_fault=None, write_count=None):
        ctx=drv.WindowsHeldContext(Path.cwd()/"fake-held-bootstrap-unused","a"*40)
        table,originals,_,_,_=observed.setup(False)
        events=[]
        surface=consumer.NativeSurface()
        source=ctx.source
        def source_connect(path):
            events.append("source_connect")
            source._started=source._connected=True
            source._root=path
            source._leases=[originals[0]]
            source._user=observed.USER
        def source_open(path,**kwargs):
            events.append("source_open")
            self.assertEqual(kwargs,{"directory":False,"create":True})
            lease=originals[len(source._leases)]
            source._leases.append(lease)
            return lease
        def write(handle,buffer,size,count,overlapped):
            events.append("write")
            originals[handle//101-1].observed.raw=C.string_at(buffer,size)
            count._obj.value=size if write_count is None else write_count
            return 1
        source.connect,source._open=source_connect,source_open
        source._win=SimpleNamespace(D=C.c_uint32,_verify_sd=observed.win._verify_sd)
        source._api=SimpleNamespace(security=lambda h:originals[h//101-1].observed.sd,
            call=lambda value,reason:owned._need(bool(value),reason),
            k=SimpleNamespace(WriteFile=write,FlushFileBuffers=lambda h:events.append("flush") or 1))
        source._backend=table
        def connect():
            ctx.sink._started=ctx.sink._connected=ctx._connected=True
        ctx.connect=connect
        ctx.guard=lambda:events.append("guard")
        saved=[]
        def persist(step,raw,digest):
            events.append(step)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
            saved.append((step,raw))
            if persist_fault and step=="prepare": raise persist_fault
        ctx.sink.persist_evidence=persist
        def backend_factory(given_source):
            self.assertIs(given_source,source)
            backend=sealing.SealTable(table,originals)
            backend.accesses={404:drv.seal.FILE_SEAL_ACCESS,505:drv.seal.MARKER_SEAL_ACCESS}
            surface.attach(originals[0].observed)
            original_view=backend.view
            def view(handle,plan):
                value=original_view(handle,plan)
                surface.attach(value)
                return value
            backend.view=view
            return backend
        surface.active=lambda:ctx.reader is not None and ctx.reader._pins is not None
        return ctx,table,events,saved,surface,backend_factory

    def test_real_prepare_barrier_collector_and_terminal_context_with_fake_native_surface(self):
        ctx,table,events,saved,surface,factory=self.setup_context()
        driver=drv.HeldDriver(ctx)
        with patch.object(drv.seal,"WindowsSealBackend",side_effect=factory): driver.run()
        self.assertEqual(driver.exit_code(),0)
        self.assertFalse(table.live)
        self.assertEqual([step for step,raw in saved],["prepare","seal_payload"])
        self.assertEqual(events.count("source_open"),2)
        self.assertEqual(events.count("write"),2)
        self.assertEqual(events.count("flush"),2)
        self.assertEqual([h for kind,h in surface.calls if kind=="read"],[404,505])
        self.assertEqual(ctx.reader._captured[0],b'{"scope":"held_consumer_probe","count":2}\n')
        self.assertTrue(ctx._prepared)
        self.assertEqual(ctx.group.owner._journal.snapshot()["commit_observation"],"not_started")

    def test_prepare_evidence_failure_retains_unreleased_writers_and_root(self):
        primary=ValueError("prepare store")
        ctx,table,events,saved,surface,factory=self.setup_context(persist_fault=primary)
        driver=drv.HeldDriver(ctx)
        with patch.object(drv.seal,"WindowsSealBackend",side_effect=factory),self.assertRaises(ValueError) as caught:
            driver.run()
        self.assertIs(caught.exception,primary)
        self.assertEqual(driver.exit_code(),81)
        self.assertEqual(set(table.live),{101,202,303})
        self.assertFalse(surface.calls)
        self.assertFalse(ctx._root_finished)

    def test_short_fixture_write_stops_before_flush_adoption_and_reader(self):
        ctx,table,events,saved,surface,factory=self.setup_context(write_count=0)
        driver=drv.HeldDriver(ctx)
        with patch.object(drv.seal,"WindowsSealBackend",side_effect=factory),self.assertRaises(owned.OwnershipError):
            driver.run()
        self.assertNotIn("flush",events)
        self.assertFalse(ctx.group.active)
        self.assertIsNone(ctx.reader)
        self.assertFalse(saved)
        # 303 was a test-table reservation; it was never registered/acquired by the context.
        self.assertEqual(set(table.live),{303})
        self.assertEqual(driver.exit_code(),1)

    def test_prepare_evidence_size_limit_precedes_store_and_writer_release(self):
        ctx,table,events,saved,surface,factory=self.setup_context()
        driver=drv.HeldDriver(ctx)
        with patch.object(drv.seal,"WindowsSealBackend",side_effect=factory), \
             patch.object(drv.bridge,"capture_record",return_value=SimpleNamespace(raw=b'x'*65537)), \
             self.assertRaises(MemoryError): driver.run()
        self.assertEqual(driver.exit_code(),80)
        self.assertFalse(saved)
        self.assertFalse(surface.calls)
        self.assertEqual(set(table.live),{101,202,303})


class ResourceBudgetTests(unittest.TestCase):
    def test_point_limit_stops_before_any_api_query(self):
        ctx=drv.WindowsHeldContext(Path.cwd()/"fake-unused","a"*40)
        ctx._points=[None]*ctx.MAX_POINTS
        with self.assertRaises(MemoryError): ctx.budget()
        self.assertEqual(len(ctx._points),1024)

    def test_memory_time_and_free_space_limits_and_normal_point(self):
        for boundary in (None,"private","working","ram","disk","time"):
            ctx=drv.WindowsHeldContext(Path.cwd()/"fake-unused","a"*40)
            def memory(process,pointer,size):
                pointer._obj.private=257*1024**2 if boundary=="private" else 20*1024**2
                pointer._obj.working=385*1024**2 if boundary=="working" else 30*1024**2
                return 1
            def performance(pointer,size):
                pointer._obj.page_size=4096
                pointer._obj.available=(1 if boundary=="ram" else 4)*1024**3//4096
                return 1
            ctx.sink._win=observed.win
            ctx.sink._api=SimpleNamespace(call=lambda value,reason:owned._need(bool(value),reason),
                k=SimpleNamespace(GetCurrentProcess=lambda:1),
                p=SimpleNamespace(GetProcessMemoryInfo=memory,GetPerformanceInfo=performance))
            ctx._start=0
            with patch.object(drv.acquisition.time,"monotonic",return_value=41 if boundary=="time" else 1), \
                 patch.object(drv.acquisition.shutil,"disk_usage",return_value=SimpleNamespace(free=(1 if boundary=="disk" else 4)*1024**3)):
                if boundary:
                    with self.assertRaises(MemoryError): ctx.budget()
                else: ctx.budget()
            self.assertEqual(len(ctx._points),1)


if __name__=="__main__":
    unittest.main()
