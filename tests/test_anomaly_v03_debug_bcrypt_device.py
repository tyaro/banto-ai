"""Fake-only three-site device observation with unused DR3 disabled."""
import ctypes as C
import struct
import unittest
from contextlib import ExitStack

from tests import test_anomaly_v03_debug_bcrypt_failure as fixtures
from tests.fixtures.anomaly_v03_debug_bcrypt_device import DebugBcryptDevice as Probe
from tests.fixtures.anomaly_v03_debug_driver import DebugDriver
from tests.fixtures.anomaly_v03_debug_transport import DBG_CONTINUE, DBG_NOT_HANDLED, TransportError
from tests.fixtures.anomaly_v03_debug_evidence_reader import interpret


class BcryptDeviceTests(unittest.TestCase):
    def fixture(self, scope, **kwargs):
        return fixtures.BcryptFailureTests().fixture(scope,device=True,**kwargs)

    def test_three_sites_and_warning_stop_with_dr3_disabled(self):
        for site,value in ((0,0xC0000022),(1,0xC0000022),(1,0x80000005),(2,0xC0000022)):
            with ExitStack() as scope,self.subTest(site=site,value=value):
                o,k,fixture,memory,regs=self.fixture(scope,site=site,value=value)
                o.run();r=o.context.row
                self.assertEqual(o.primary.reason,"bcrypt_device_observed_stop")
                self.assertEqual(o.context.state,"completed")
                self.assertEqual((r["hit_index"],r["status_u32"],r["caller_rva"]),(site,value,Probe.CALLER_RVAS[site]))
                self.assertEqual((r["get_attempts"],r["read_attempts"],r["confirmed_bytes"]),(3,4,1766))
                self.assertEqual(k.GetThreadContext.call_count,4)
                k.SetThreadContext.assert_called_once()
                self.assertEqual(k.ReadProcessMemory.call_count,7)
                self.assertEqual(sum(c.args[3] for c in k.ReadProcessMemory.call_args_list),1841)
                self.assertEqual(k.ReadProcessMemory.call_args.args[1].value,
                                 fixtures.BcryptFailureTests.RSP+Probe.CALLER_OFFSETS[site])
                request=struct.unpack("<6Q",bytes.fromhex(r["requested_debug_hex"]))
                self.assertEqual(request[3],0)
                self.assertEqual(request[5]&~0x400,0x15)
                self.assertEqual([c.args[2] for c in k.ContinueDebugEvent.call_args_list],
                                 [DBG_CONTINUE]*4+[DBG_NOT_HANDLED,DBG_CONTINUE])
                self.assertEqual(o.result["teardown_status"],"pass")
                self.assertEqual(o.stop.handles,[None,None])
                fixture.cleanup.assert_not_called()
                saved=interpret(o.evidence.buffer.raw[:o.evidence.size])
                self.assertEqual(saved.private_metadata["context"]["row"]["status_u32"],value)
                self.assertNotIn("response_information",r)
                self.assertFalse(o.result["native_accepted"])

    def test_open_helper_uses_r12_before_eax_move(self):
        with ExitStack() as scope:
            o,k,*unused=self.fixture(scope,site=0,value=0xC0000022)
            original=k.GetThreadContext.side_effect
            def get(*args):
                ok=original(*args)
                if args[1].value==o.context.context_pointer.value and o.context.row["get_attempts"]==3:
                    struct.pack_into("<I",o.context.context,120,0)
                return ok
            k.GetThreadContext.side_effect=get
            o.run()
            self.assertEqual(o.context.state,"completed")
            self.assertEqual(o.context.row["status_u32"],0xC0000022)

    def test_context_status_and_unused_register_mismatch_prevent_caller(self):
        faults=((0,216,0),(1,120,0),(1,216,1),(0,168,0),(0,176,1),(0,232,1),(0,240,0),
                (0,152,0x30001),(0,96,0x50000000),(0,104,8),(0,112,0x455),(2,168,0),(2,240,8))
        for site,offset,value in faults:
            with ExitStack() as scope,self.subTest(site=site,offset=offset):
                o,k,*unused=self.fixture(scope,site=site,value=0xC0000022)
                original=k.GetThreadContext.side_effect
                def get(*args):
                    ok=original(*args)
                    if args[1].value==o.context.context_pointer.value and o.context.row["get_attempts"]==3:
                        struct.pack_into("<Q",o.context.context,offset,value)
                    return ok
                k.GetThreadContext.side_effect=get
                o.run()
                self.assertNotEqual(o.context.state,"completed")
                self.assertEqual(k.ReadProcessMemory.call_count,6)
                self.assertIn("context_hex",o.context.row)
                self.assertNotIn("caller_rva",o.context.row)
                self.assertEqual(o.result["teardown_status"],"pass")

    def test_caller_faults_keep_partial_evidence_and_stop_without_retry(self):
        for fault in ("false","short","oversize","memory","caller","pending","lifetime"):
            with ExitStack() as scope,self.subTest(fault=fault):
                o,k,*unused=self.fixture(scope,site=0,value=0xC0000022)
                original=k.ReadProcessMemory.side_effect
                def read(*args):
                    if k.ReadProcessMemory.call_count==7 and fault=="memory":raise MemoryError()
                    ok=original(*args)
                    if k.ReadProcessMemory.call_count==7:
                        if fault=="false":return False
                        if fault=="short":args[4].contents.value=7
                        if fault=="oversize":args[4].contents.value=9
                        if fault=="caller":C.memset(args[2],0,8)
                        if fault=="pending":o.transport.buffers[o.transport.pending].info.exception.record.information[14]=1
                        if fault=="lifetime":o.images.rows[2]["status"]="unconfirmed"
                    return ok
                k.ReadProcessMemory.side_effect=read
                o.run()
                self.assertNotEqual(o.context.state,"completed")
                self.assertEqual(k.ReadProcessMemory.call_count,7)
                self.assertNotIn("caller_rva",o.context.row)
                if fault=="memory":
                    self.assertTrue(o.resource_stop)
                    k.WriteFile.assert_not_called()
                else:self.assertIn("caller_hex",o.context.row)
                self.assertEqual(o.result["teardown_status"],"pass")

    def test_name_literal_must_match_before_set(self):
        with ExitStack() as scope:
            o,k,fixture,memory,regs=self.fixture(scope,hit=False)
            memory[fixtures.BcryptFailureTests.MODULE+0x1F098]=b"Y"*30
            o.run()
            self.assertEqual(o.primary.reason,"bcrypt_code_mismatch")
            k.SetThreadContext.assert_not_called()
            self.assertEqual(k.ReadProcessMemory.call_count,6)
            self.assertEqual(o.bootstrap.row["continue_state"],"not_started")

    def test_removed_response_site_is_unrelated_and_not_reselected(self):
        with ExitStack() as scope:
            o,k,*unused=self.fixture(scope)
            original=k.WaitForDebugEventEx.side_effect
            def deliver(pointer,timeout):
                ok=original(pointer,timeout)
                if pointer.contents.kind==1 and o.context.state=="armed":
                    pointer.contents.info.exception.record.address=fixtures.BcryptFailureTests.MODULE+0x8131
                return ok
            k.WaitForDebugEventEx.side_effect=deliver
            o.run()
            self.assertEqual(o.primary.reason,"bcrypt_exception")
            self.assertEqual(k.GetThreadContext.call_count,3)
            with self.assertRaises(TransportError):o.context.capture(lambda:None)
            self.assertEqual(k.GetThreadContext.call_count,3)

    def test_exclusive_options_and_no_hit(self):
        with ExitStack() as scope:
            o,k,*unused=self.fixture(scope,hit=False)
            o.run()
            self.assertEqual(o.primary.reason,"init_failure_not_observed")
            self.assertNotIn("status_u32",o.context.row)
        self.assertNotIsInstance(DebugDriver().context,Probe)
        invalid=[{"bcrypt_device":value} for value in (True,1,None)]
        invalid += [{"bcrypt_device":True,"bootstrap":True},{"bcrypt_device":True,"detached_console":True}]
        invalid += [dict(bcrypt_device=True,bootstrap=True,detached_console=True,**{key:True})
                    for key in ("unload_entry","init_return","console_failure","init_failure","bcrypt_failure","bcrypt_detail")]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs),self.assertRaises(TransportError):DebugDriver(**kwargs)


if __name__=="__main__":
    unittest.main()
