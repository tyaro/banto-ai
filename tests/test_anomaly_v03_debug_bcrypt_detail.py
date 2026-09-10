"""Fake-only deeper bcrypt sites, fixed caller frames and terminal reads."""
import ctypes as C
import struct
import unittest
from contextlib import ExitStack

from tests import test_anomaly_v03_debug_bcrypt_failure as fixtures
from tests.fixtures.anomaly_v03_debug_bcrypt_detail import DebugBcryptDetail as Probe
from tests.fixtures.anomaly_v03_debug_driver import DebugDriver
from tests.fixtures.anomaly_v03_debug_transport import DBG_CONTINUE, DBG_NOT_HANDLED, TransportError
from tests.fixtures.anomaly_v03_debug_evidence_reader import interpret


class BcryptDetailTests(unittest.TestCase):
    def fixture(self, scope, **kwargs):
        return fixtures.BcryptFailureTests().fixture(scope,detail=True,**kwargs)

    def test_four_sites_keep_values_and_fixed_caller_without_continuing_hit(self):
        for site,value in ((0,0xC0000022),(1,5),(1,0),(2,5),(3,0xC0000022)):
            with ExitStack() as scope,self.subTest(site=site,value=value):
                o,k,fixture,memory,regs=self.fixture(scope,site=site,value=value)
                o.run();r=o.context.row
                self.assertEqual(o.primary.reason,"bcrypt_detail_observed_stop")
                self.assertEqual(o.context.state,"completed")
                self.assertEqual((r["hit_index"],r["status_u32"],r["caller_rva"]),(site,value,Probe.CALLER_RVAS[site]))
                self.assertEqual((r["get_attempts"],r["read_attempts"],r["confirmed_bytes"]),(3,4,1798))
                self.assertEqual(k.GetThreadContext.call_count,4)
                k.SetThreadContext.assert_called_once()
                self.assertEqual(k.ReadProcessMemory.call_count,7)
                self.assertEqual(sum(c.args[3] for c in k.ReadProcessMemory.call_args_list),1873)
                self.assertEqual(k.ReadProcessMemory.call_args.args[1].value,
                                 fixtures.BcryptFailureTests.RSP+Probe.CALLER_OFFSETS[site])
                self.assertEqual([c.args[2] for c in k.ContinueDebugEvent.call_args_list],
                                 [DBG_CONTINUE]*4+[DBG_NOT_HANDLED,DBG_CONTINUE])
                self.assertEqual(o.result["teardown_status"],"pass")
                self.assertEqual(o.stop.handles,[None,None])
                fixture.cleanup.assert_not_called()
                saved=interpret(o.evidence.buffer.raw[:o.evidence.size])
                self.assertEqual(saved.private_metadata["context"]["row"]["status_u32"],value)
                self.assertFalse(o.result["native_accepted"])

    def test_cleanup_registers_remain_separate_and_unclassified(self):
        for eax,edi,ebp in ((0,8,0),(5,5,0),(0xC0000022,0,0xC0000022)):
            with ExitStack() as scope,self.subTest(eax=eax,edi=edi,ebp=ebp):
                o,k,*unused=self.fixture(scope,site=2,value=eax)
                original=k.GetThreadContext.side_effect
                def get(*args):
                    ok=original(*args)
                    if args[1].value==o.context.context_pointer.value and o.context.row["get_attempts"]==3:
                        struct.pack_into("<I",o.context.context,160,ebp)
                        struct.pack_into("<I",o.context.context,176,edi)
                    return ok
                k.GetThreadContext.side_effect=get
                o.run()
                self.assertEqual(o.context.state,"completed")
                r=o.context.row
                self.assertEqual((r["status_u32"],r["cleanup_edi"],r["cleanup_ebp"]),(eax,edi,ebp))
                self.assertEqual(r["status_domain"],"mixed_cleanup_candidates")

    def test_branch_or_frame_mismatch_retains_context_before_caller(self):
        for site,offset,kind,value in ((0,120,"I",5),(0,144,"I",1),(3,120,"I",0),
                (1,168,"Q",0),(1,240,"Q",1),(1,160,"I",1),(2,240,"Q",1),
                (1,152,"Q",0x30001),(2,152,"Q",Probe.USER_MAX-0x100)):
            with ExitStack() as scope,self.subTest(site=site,offset=offset):
                o,k,*unused=self.fixture(scope,site=site,value=0xC0000022 if site in (0,3) else 5)
                original=k.GetThreadContext.side_effect
                def get(*args):
                    ok=original(*args)
                    if args[1].value==o.context.context_pointer.value and o.context.row["get_attempts"]==3:
                        struct.pack_into("<"+kind,o.context.context,offset,value)
                    return ok
                k.GetThreadContext.side_effect=get
                o.run()
                self.assertNotEqual(o.context.state,"completed")
                self.assertEqual(k.ReadProcessMemory.call_count,6)
                self.assertIn("context_hex",o.context.row)
                self.assertNotIn("caller_rva",o.context.row)
                self.assertEqual(o.result["teardown_status"],"pass")

    def test_caller_read_failures_keep_bounds_and_ownership(self):
        for fault in ("false","short","oversize","memory","caller","pending","lifetime"):
            with ExitStack() as scope,self.subTest(fault=fault):
                o,k,*unused=self.fixture(scope,site=1)
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

    def test_third_code_window_is_required_before_set(self):
        with ExitStack() as scope:
            o,k,fixture,memory,regs=self.fixture(scope,hit=False)
            memory[fixtures.BcryptFailureTests.MODULE+0x11140]=b"Y"*475
            o.run()
            self.assertEqual(o.primary.reason,"bcrypt_code_mismatch")
            self.assertEqual(k.ReadProcessMemory.call_count,6)
            k.SetThreadContext.assert_not_called()
            self.assertEqual(o.bootstrap.row["continue_state"],"not_started")
            self.assertEqual(o.result["teardown_status"],"pass")

    def test_options_are_exclusive_and_no_hit_does_not_fabricate_status(self):
        with ExitStack() as scope:
            o,k,*unused=self.fixture(scope,hit=False)
            o.run()
            self.assertEqual(o.primary.reason,"init_failure_not_observed")
            self.assertNotIn("status_u32",o.context.row)
        self.assertNotIsInstance(DebugDriver().context,Probe)
        invalid=[{"bcrypt_detail":x} for x in (True,1,None)]
        invalid += [{"bcrypt_detail":True,"bootstrap":True},{"bcrypt_detail":True,"detached_console":True}]
        invalid += [dict(bcrypt_detail=True,bootstrap=True,detached_console=True,**{key:True})
                    for key in ("unload_entry","init_return","console_failure","init_failure","bcrypt_failure")]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs),self.assertRaises(TransportError):DebugDriver(**kwargs)


if __name__=="__main__":
    unittest.main()
