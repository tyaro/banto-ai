"""Worker pin/output/retention faults; no native process or source fixture."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_held_launch as launch
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests import test_anomaly_v03_held_driver as driver_tests


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.live_patch=patch.object(launch,"_LIVE_WORKER",None)
        self.live_patch.start()
        self.addCleanup(self.live_patch.stop)
        self.ctx=driver_tests.Context()
        self.writes=[]

    def write(self,fd,raw):
        self.writes.append((fd,raw))
        return len(raw)

    def execute(self,write=None):
        return launch.execute(self.ctx,"a"*40,"b"*64,12,write or self.write)

    def test_real_driver_success_has_pins_collection_and_no_raw_bytes_in_single_output(self):
        self.assertEqual(self.execute(),0)
        self.assertEqual(len(self.writes),1)
        report=json.loads(self.writes[0][1])
        self.assertEqual(report["source_revision"],"a"*40)
        self.assertEqual(report["input_sha256"],"b"*64)
        self.assertEqual(report["pinned_source_count"],12)
        self.assertEqual(report["context"]["reader"]["collection"],"complete")
        self.assertEqual(len(report["context"]["reader"]["files"]),2)
        self.assertNotIn(b'bytes_b64',self.writes[0][1])
        self.assertFalse(self.ctx.table.live)
        self.assertIs(launch._LIVE_WORKER.context,self.ctx)

    def test_unknown_child_and_output_error_keeps_context_parent_and_exit81(self):
        primary=ValueError("child")
        self.ctx.table.hooks[404]=driver_tests.fail(primary)
        def write(fd,raw):
            self.writes.append((fd,raw))
            raise OSError("output")
        self.assertEqual(self.execute(write),81)
        self.assertEqual(len(self.writes),1)
        self.assertIs(launch._LIVE_WORKER._error,primary)
        self.assertTrue({101,404,601,602,701,702}.issubset(self.ctx.table.live))

    def test_report_failure_preserves_retained_code_without_output(self):
        primary=ValueError("child")
        self.ctx.table.hooks[404]=driver_tests.fail(primary)
        self.ctx.snapshot=driver_tests.fail(RuntimeError("report"))
        self.assertEqual(self.execute(),81)
        self.assertFalse(self.writes)
        self.assertIs(launch._LIVE_WORKER._error,primary)

    def test_report_resource_failure_escalates_and_uses_one_constant_notice(self):
        primary=ValueError("child")
        self.ctx.table.hooks[404]=driver_tests.fail(primary)
        self.ctx.snapshot=driver_tests.fail(MemoryError("report"))
        self.assertEqual(self.execute(),80)
        self.assertEqual(self.writes,[(1,launch.RESOURCE_NOTICE)])
        self.assertIs(launch._LIVE_WORKER._error,primary)
        self.assertTrue(launch._LIVE_WORKER._retained)

    def test_initial_resource_stop_never_allocates_regular_report_and_never_retries_output(self):
        self.ctx._resource=True
        self.ctx.snapshot=driver_tests.fail(AssertionError("report after resource"))
        def lost(fd,raw):
            self.writes.append((fd,raw))
            raise MemoryError("write")
        self.assertEqual(self.execute(lost),80)
        self.assertEqual(self.writes,[(1,launch.RESOURCE_NOTICE)])

    def test_short_wrong_type_and_lost_writes_are_single_attempt_failures(self):
        for result in (0,True,None,"1"):
            with self.subTest(result=result),patch.object(launch,"_LIVE_WORKER",None):
                self.ctx=driver_tests.Context()
                calls=[]
                def write(fd,raw):
                    calls.append(raw)
                    return result
                self.assertEqual(self.execute(write),1)
                self.assertEqual(len(calls),1)

    def test_output_memory_failure_after_completed_read_escalates_without_fallback(self):
        def write(fd,raw):
            self.writes.append((fd,raw))
            raise MemoryError("output")
        self.assertEqual(self.execute(write),80)
        self.assertEqual(len(self.writes),1)
        self.assertNotEqual(self.writes[0][1],launch.RESOURCE_NOTICE)

    def test_envelope_budget_becomes_resource_notice_before_any_output(self):
        with patch.object(launch,"MAX_OUTPUT_BYTES",1):
            self.assertEqual(self.execute(),80)
        self.assertEqual(self.writes,[(1,launch.RESOURCE_NOTICE)])

    def test_worker_cannot_be_reused_even_after_success(self):
        self.assertEqual(self.execute(),0)
        with self.assertRaises(owned.OwnershipError): self.execute()
        self.assertEqual(len(self.writes),1)


class PinTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="banto-held-pin-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.name="tests/fixtures/local.py"
        file=self.root/self.name
        file.parent.mkdir(parents=True)
        file.write_bytes(b"# local inert pin test\n")
        self.pin={"implementation_revision":"a"*40,"sources":{self.name:{"bytes":file.stat().st_size,
            "sha256":hashlib.sha256(file.read_bytes()).hexdigest()}}}
        self.pin_path=self.root/"input-pin.json"
        self.digest=self.save()
        self.git_calls=[]

    def save(self):
        raw=json.dumps(self.pin).encode()
        self.pin_path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def git(self,args,**kwargs):
        self.git_calls.append(args)
        if args[1]=="rev-parse":return "a"*40+"\n"
        if args[1]=="status":return b""
        return self.name.encode()+b"\0"

    def validate(self):
        return launch.validate_inputs(self.root,self.pin_path,"a"*40,self.digest)

    def test_exact_clean_head_full_inventory_and_raw_hash_match(self):
        with patch.object(launch.subprocess,"check_output",side_effect=self.git):
            self.assertEqual(self.validate(),1)
        self.assertEqual(len(self.git_calls),3)

    def test_dirty_or_wrong_head_stops_before_reading_input(self):
        for outputs in (("c"*40+"\n",),("a"*40+"\n",b" M file")):
            with patch.object(launch.subprocess,"check_output",side_effect=outputs), \
                 patch.object(launch,"_read") as read,self.assertRaises(owned.OwnershipError): self.validate()
            read.assert_not_called()

    def test_changed_bytes_or_missing_inventory_is_rejected(self):
        for mode in ("source","extra","missing"):
            with self.subTest(mode=mode):
                if mode=="source": (self.root/self.name).write_bytes(b"# changed\n")
                elif mode=="extra": self.pin["sources"]["tests/fixtures/extra.py"]={"bytes":0,"sha256":"0"*64}
                else:self.pin["sources"].clear()
                self.digest=self.save()
                with patch.object(launch.subprocess,"check_output",side_effect=self.git),self.assertRaises(owned.OwnershipError):
                    self.validate()

    def test_pin_digest_shape_and_size_are_checked_before_sources(self):
        with patch.object(launch.subprocess,"check_output",side_effect=self.git), \
             patch.object(launch,"source_names") as names:
            self.digest="0"*64
            with self.assertRaises(owned.OwnershipError):self.validate()
            self.digest=self.save()
            with patch.object(launch,"MAX_PIN_BYTES",1),self.assertRaises(owned.OwnershipError):self.validate()
            self.pin["extra"]=1
            self.digest=self.save()
            with self.assertRaises(owned.OwnershipError):self.validate()
            names.assert_not_called()

    def test_path_and_inventory_bounds_reject_untrusted_git_listing(self):
        for name in ("../bad.py","/bad.py","C:/bad.py","tests\\bad.py"):
            with patch.object(launch.subprocess,"check_output",return_value=name.encode()+b"\0"), \
                 self.assertRaises(owned.OwnershipError):launch.source_names(self.root)
        for raw in (b"",b"a.py\0"*2,b"".join(f"a{i}.py\0".encode() for i in range(513))):
            with patch.object(launch.subprocess,"check_output",return_value=raw), \
                 self.assertRaises(owned.OwnershipError):launch.source_names(self.root)

    def test_source_size_and_pin_types_are_bounded(self):
        for size in (True,-1,launch.MAX_SOURCE_BYTES+1):
            self.pin["sources"][self.name]["bytes"]=size
            self.digest=self.save()
            with patch.object(launch.subprocess,"check_output",side_effect=self.git),self.assertRaises(owned.OwnershipError):
                self.validate()

    def test_invalid_pin_prevents_context_and_attempt_creation(self):
        with patch.object(launch,"validate_inputs",side_effect=ValueError("pin")), \
             patch.object(launch,"_LIVE_WORKER",None):
            factory=driver_tests.fail(AssertionError("context before pin"))
            with self.assertRaises(ValueError): launch.launch(self.root,self.root,"a"*40,"b"*64,lambda *args:None,context_factory=factory)
        self.assertFalse((self.root/"attempt-1").exists())

    def test_exclusive_attempt_collision_does_not_execute_or_inspect_old_case(self):
        (self.root/"attempt-1").mkdir()
        with patch.object(launch,"validate_inputs",return_value=1),patch.object(launch,"execute") as execute, \
             patch.object(launch,"_LIVE_WORKER",None),self.assertRaises(FileExistsError):
            launch.launch(self.root,self.root,"a"*40,"b"*64,lambda *args:None,context_factory=lambda *args:object())
        execute.assert_not_called()


if __name__=="__main__":unittest.main()
