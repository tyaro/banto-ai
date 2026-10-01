"""Resource thresholds without exhausting the host; tiny owned stop cases."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from banto_ai import _anomaly_v03_fixture_budget as budgets
from banto_ai import anomaly_v03_process_supervisor as supervisor
from banto_ai import anomaly_v03_fixture_audit_worker as audit
from tests.test_anomaly_v03_engineering import fixture_context

HEALTHY = {'commit_total_bytes':4*1024**3,'commit_limit_bytes':8*1024**3,'commit_headroom_bytes':4*1024**3,
           'free_ram_bytes':4*1024**3,'free_disk_bytes':40*1024**3,'parent_peak_private_bytes':32*1024**2}


class FixtureBudgetTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='banto-budget-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve()

    def test_limits_reject_relaxation_nonfinite_and_boolean(self):
        for key,value in [('wall_seconds',121),('wall_seconds',float('nan')),('directory_bytes',True),
                          ('directory_entries',0),('minimum_commit_headroom_bytes',1)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):budgets.limits(budgets.DEFAULTS|{key:value})
        with self.assertRaises(ValueError):budgets.limits({})

    def test_threshold_equality_is_allowed_and_each_breach_latches(self):
        equal=HEALTHY|{'parent_peak_private_bytes':budgets.DEFAULTS['parent_private_bytes'],
            'commit_total_bytes':6*1024**3,'commit_headroom_bytes':2*1024**3,'free_ram_bytes':2*1024**3,'free_disk_bytes':5*1024**3}
        for key,delta,reason in [('parent_peak_private_bytes',1,'pipeline_parent_memory_limit'),
            ('free_ram_bytes',-1,'pipeline_free_ram'),('free_disk_bytes',-1,'pipeline_free_disk'),
            ('commit_headroom_bytes',-1,'pipeline_commit_headroom')]:
            with self.subTest(key=key),patch.object(budgets,'system_snapshot',return_value=equal.copy()) as sample:
                monitor=budgets.FixtureBudget(self.root);monitor.checkpoint();self.assertIsNone(monitor.probe())
                bad=equal|{key:equal[key]+delta}
                if key=='commit_headroom_bytes':bad['commit_total_bytes']+=1
                sample.return_value=bad
                with self.assertRaises(budgets.resources.ResourceStop):monitor.checkpoint()
                sample.return_value=HEALTHY.copy();report=monitor.close()
                self.assertEqual(report['stop_reason'],reason);self.assertTrue(report['monitor_exit_confirmed'])

    def test_wall_limit_includes_parent_phase(self):
        with patch.object(budgets,'system_snapshot',return_value=HEALTHY.copy()):
            monitor=budgets.FixtureBudget(self.root);monitor.started-=121
            with self.assertRaisesRegex(budgets.resources.ResourceStop,'pipeline_wall_limit'):monitor.checkpoint()
            self.assertFalse(monitor.close()['passed'])

    def test_directory_counts_nested_outputs_and_preserves_burst(self):
        (self.root/'payload').mkdir();(self.root/'payload/a').write_bytes(b'12345');(self.root/'log').write_bytes(b'6789')
        self.assertEqual(budgets.directory_snapshot(self.root,10),{'directory_bytes':9,'directory_entries':3})
        with patch.object(budgets,'system_snapshot',return_value=HEALTHY.copy()):
            monitor=budgets.FixtureBudget(self.root,budgets.DEFAULTS|{'directory_bytes':8})
            with self.assertRaisesRegex(budgets.resources.ResourceStop,'pipeline_directory_limit'):monitor.start()
            report=monitor.close()
        self.assertEqual(report['last']['directory_bytes'],9);self.assertEqual((self.root/'payload/a').read_bytes(),b'12345')

    def test_scan_inventory_depth_and_hardlink_fail_closed(self):
        (self.root/'a').write_bytes(b'one');(self.root/'b').write_bytes(b'two')
        with self.assertRaisesRegex(budgets.resources.ResourceStop,'inventory'):budgets.directory_snapshot(self.root,1)
        nested=self.root
        for i in range(9):nested=nested/str(i);nested.mkdir()
        with self.assertRaisesRegex(budgets.resources.ResourceStop,'depth'):budgets.directory_snapshot(self.root,30)
        linkroot=self.root/'links';linkroot.mkdir();os.link(self.root/'a',linkroot/'alias')
        with self.assertRaisesRegex(budgets.resources.ResourceStop,'unsafe'):budgets.directory_snapshot(linkroot,10)

    def test_observation_failure_stops_and_missing_commit_is_not_zero(self):
        for sample in (OSError('observation unavailable'),HEALTHY|{'commit_headroom_bytes':True}):
            with self.subTest(sample=type(sample).__name__),patch.object(budgets,'system_snapshot') as observe:
                if isinstance(sample,Exception):observe.side_effect=sample
                else:observe.return_value=sample
                monitor=budgets.FixtureBudget(self.root)
                with self.assertRaisesRegex(budgets.resources.ResourceStop,'observation_error'):monitor.start()
                report=monitor.close();self.assertIsNotNone(report['observation_error'])

    def test_background_monitor_notices_pressure_during_parent_work(self):
        pressure=threading.Event()
        def sample(root):
            return HEALTHY|({'free_disk_bytes':1} if pressure.is_set() else {})
        with patch.object(budgets,'system_snapshot',side_effect=sample):
            monitor=budgets.FixtureBudget(self.root);monitor.start()
            try:
                pressure.set();monitor._thread.join(timeout=2)
                self.assertEqual(monitor.probe(),'pipeline_free_disk')
            finally:report=monitor.close()
        self.assertTrue(report['monitor_exit_confirmed']);self.assertGreaterEqual(report['samples'],2)

    def test_shared_budget_does_not_reset_for_next_directory(self):
        with patch.object(budgets,'system_snapshot',return_value=HEALTHY.copy()):
            outer=budgets.FixtureBudget(self.root,budgets.DEFAULTS|{'directory_bytes':12});outer.start()
            try:
                a=self.root/'analysis';a.mkdir();(a/'output').write_bytes(b'12345678');outer.checkpoint()
                b=self.root/'audit';b.mkdir();inner=budgets.FixtureBudget(b,upstream=outer);inner.start()
                try:
                    (b/'output').write_bytes(b'12345678')
                    with self.assertRaisesRegex(budgets.resources.ResourceStop,'directory_limit'):outer.checkpoint()
                    self.assertEqual(inner.probe(),'pipeline_directory_limit')
                finally:inside=inner.close()
                self.assertFalse(inside['passed']);self.assertEqual(inside['shared_root'],str(self.root))
            finally:outside=outer.close()
        self.assertEqual(outside['last']['directory_bytes'],16)

    def test_shared_budget_cannot_cover_unrelated_or_closed_root(self):
        parent=budgets.FixtureBudget(self.root)
        other=self.root/'child';other.mkdir()
        with self.assertRaises(ValueError):budgets.FixtureBudget(other,upstream=parent)

    def test_finish_preserves_unreaped_owner_on_save_or_close_error(self):
        owner=object();error=supervisor.UnreapedWorker(owner,{'worker_exit_confirmed':False})
        with patch.object(budgets,'system_snapshot',return_value=HEALTHY.copy()):
            monitor=budgets.FixtureBudget(self.root)
            with patch.object(budgets.io,'_exclusive',side_effect=OSError('save failure')):
                with self.assertRaises(supervisor.UnreapedWorker) as caught:budgets.finish(monitor,self.root,{},error)
            self.assertIs(caught.exception,error);self.assertIs(caught.exception.process,owner)
            with patch.object(monitor,'close',side_effect=KeyboardInterrupt()):
                with self.assertRaises(supervisor.UnreapedWorker) as caught:budgets.finish(monitor,self.root,{},error)
            self.assertIs(caught.exception,error);self.assertIs(caught.exception.resource_monitor,monitor)

    def test_post_phase_burst_prevents_success_at_finish_and_reserve_is_bounded(self):
        with patch.object(budgets,'system_snapshot',return_value=HEALTHY.copy()):
            monitor=budgets.FixtureBudget(self.root,budgets.DEFAULTS|{'directory_bytes':4});monitor.start()
            (self.root/'payload').write_bytes(b'12345');result={'status':'verified'}
            budgets.finish(monitor,self.root,result)
        self.assertEqual(result['status'],'failed');self.assertFalse(result['resource_budget_passed'])
        with self.assertRaisesRegex(budgets.resources.ResourceStop,'receipt_limit'):budgets.save_result(self.root,{'large':'x'*budgets.RECEIPT_RESERVE})

    @unittest.skipUnless(os.name=='nt','owned Windows child')
    def test_real_child_is_reaped_after_small_directory_burst(self):
        monitor=budgets.FixtureBudget(self.root,budgets.DEFAULTS|{'directory_bytes':65536});monitor.start()
        argv=[sys.executable,'-I','-S','-B','-c',"from pathlib import Path;import sys,time;Path(sys.argv[1]).write_bytes(b'x'*65537);time.sleep(20)",str(self.root/'burst.bin')]
        try:
            result=supervisor.supervise(argv,self.root,self.root/'control',{'wall_seconds':5,'private_bytes':128*1024**2,'output_bytes':1024},
                runtime_probe=lambda:fixture_context()[1],resource_probe=monitor.probe)
        finally:report=monitor.close()
        self.assertEqual(result['stop_reason'],'pipeline_directory_limit');self.assertTrue(result['worker_exit_confirmed'])
        self.assertFalse(report['passed']);self.assertEqual((self.root/'burst.bin').stat().st_size,65537)

    @unittest.skipUnless(os.name=='nt','owned Windows child')
    def test_real_child_reaped_for_injected_commit_pressure_without_allocating_ram(self):
        started=threading.Event()
        def sample(root):
            return HEALTHY|({'commit_total_bytes':7*1024**3,'commit_headroom_bytes':1024**3} if started.is_set() else {})
        with patch.object(budgets,'system_snapshot',side_effect=sample):
            monitor=budgets.FixtureBudget(self.root);monitor.start()
            try:
                result=supervisor.supervise([sys.executable,'-I','-S','-B','-c','import time;time.sleep(20)'],self.root,self.root/'control',
                    {'wall_seconds':5,'private_bytes':128*1024**2,'output_bytes':1024},runtime_probe=lambda:fixture_context()[1],
                    on_started=lambda process:started.set(),resource_probe=monitor.probe)
            finally:report=monitor.close()
        self.assertEqual(result['stop_reason'],'pipeline_commit_headroom');self.assertTrue(result['worker_exit_confirmed'])
        self.assertEqual(report['stop_reason'],'pipeline_commit_headroom')


@unittest.skipUnless(os.name=='nt' and sys.version_info[:2]==(3,14),'Windows fixture worker')
class BudgetIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_anomaly_v03_fixture_audit_worker import hand,write_request
        cls.write_request=staticmethod(write_request);cls.fixture=hand.hand.hand.invented_input();cls.document=hand.connected(cls.fixture)
        cls.revision=subprocess.check_output(['git','-C',str(audit.ROOT),'rev-parse','HEAD'],text=True).strip()

    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='banto-budget-integration-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.receipts=self.root/'receipts';self.receipts.mkdir()
        self.request=self.write_request(self.root/'inputs',self.revision,self.fixture,self.document)

    def test_pressure_before_launch_saves_failure_and_launches_nothing(self):
        with patch.object(budgets,'system_snapshot',return_value=HEALTHY|{'free_ram_bytes':1}),patch.object(audit,'_git_sources',side_effect=AssertionError('source read')):
            result=audit.audit_with_evidence(self.request,expected_revision=self.revision,receipt_parent=self.receipts,receipt_name='blocked')
        self.assertEqual(result['status'],'failed');self.assertEqual(result['reason'],'pipeline_free_ram')
        self.assertIsNone(result['worker_pid']);self.assertFalse(result['resource_budget_passed'])
        self.assertTrue((Path(result['check_directory'])/'resource-budget.json').exists())

    def test_post_child_pressure_preserves_payload_but_blocks_parent_binding(self):
        original=supervisor.supervise
        def burst(*args,**kwargs):
            result=original(*args,**kwargs);self.assertEqual(result['status'],'complete',result)
            (args[2].parent/'post-child.bin').write_bytes(b'x'*(512*1024));return result
        with patch.object(supervisor,'supervise',side_effect=burst),patch.object(audit.dependencies,'verify_pair',side_effect=AssertionError('binding after stop')):
            result=audit.audit_with_evidence(self.request,expected_revision=self.revision,receipt_parent=self.receipts,
                receipt_name='post-child',budget_limits=budgets.DEFAULTS|{'directory_bytes':512*1024})
        self.assertEqual(result['reason'],'pipeline_directory_limit');self.assertTrue(result['worker_exit_confirmed'])
        self.assertEqual(result['status'],'failed');self.assertFalse(result['fixture_numerical_audit_performed'])
        target=Path(result['check_directory']);self.assertTrue((target/'payload/primary-audit.json').exists())
        self.assertFalse((target/'evidence.json').exists())


if __name__=='__main__':unittest.main()
