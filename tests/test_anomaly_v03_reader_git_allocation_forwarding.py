"""Pinned allocation forwarding: fake profiles/stages/supervisor, no native run."""
import copy
from pathlib import Path
from unittest.mock import patch
import unittest

from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_reader_git_plan_forwarding as plans
from tests import test_anomaly_v03_reader_git_parent_connection as callers


class ReaderGitAllocationForwardingTests(unittest.TestCase):
    def setUp(self):
        self.f=plans.ReaderGitPlanForwardingTests()
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.limits={operation:{'receipt.json':16384,'stdout.bin':maximum,'stderr.bin':16384,
            'partial-archive.bin':65536} for operation,maximum in
            (('head',128),('status',65536),('source_blob',131072))}
        self.f.value.update(format=whole.READER_PIPE_PLAN_FORMAT,pipe_raw_limits=copy.deepcopy(self.limits))
        self.f.entry=self.f.save(self.f.value)

    def caller(self):
        self.f.doCleanups()  # Restore the composing fixture ROOT before the caller fixture reads its registry.
        self.g=callers.ReaderGitCallerConnectionTests()
        self.g.setUp();self.addCleanup(self.g.doCleanups)
        self.g.plan['pipe_raw_limits']=copy.deepcopy(self.limits)
        return self.g

    def test_new_canonical_format_and_external_pin_resolve_exact_independent_allocation(self):
        plan=self.f.load()
        self.assertEqual(set(plan),{'channel_root','policy','source_pins','pipe_raw_limits'})
        self.assertEqual(plan['pipe_raw_limits'],self.limits)
        plan['pipe_raw_limits']['source_blob']['stdout.bin']=1
        self.assertEqual(self.f.load()['pipe_raw_limits'],self.limits)
        self.assertFalse(self.f.f.outer.exists());self.assertIs(self.f.value['formal_permission'],False)

    def test_old_format_cannot_gain_allocation_and_new_format_cannot_omit_it(self):
        variants=[]
        old=copy.deepcopy(self.f.value);old['format']=whole.READER_PLAN_FORMAT;variants.append(old)
        missing=copy.deepcopy(self.f.value);missing.pop('pipe_raw_limits');variants.append(missing)
        for value in variants:
            with self.subTest(value=value),self.assertRaises(ValueError):self.f.load(self.f.save(value))
        self.assertFalse(self.f.f.outer.exists())

    def test_changed_allocation_raw_is_rejected_by_original_plan_pin_before_source_read(self):
        changed=copy.deepcopy(self.f.value);changed['pipe_raw_limits']['source_blob']['stdout.bin']=65536
        Path(self.f.entry['path']).write_bytes(whole.generated.v.canonical_json(changed))
        with patch.object(reader,'selected_source') as read,self.assertRaises(ValueError):self.f.load()
        read.assert_not_called();self.assertFalse(self.f.f.outer.exists())

    def test_real_upper_run_reopens_same_pin_and_forwards_limits_with_original_linked_budget(self):
        result,generated,_=self.f.execute()
        generated.assert_called_once();self.assertEqual(self.f.forwarded['reader_git_plan']['pipe_raw_limits'],self.limits)
        self.assertEqual(result['reader_git_plan_pin'],self.f.entry['expected_pin'])
        self.assertEqual(self.f.forwarded['outer_budget'].outer.roots['outer'],self.f.f.outer)
        self.assertEqual(result['status'],'failed');self.assertFalse(result['formal_permission'])
        # The stage is fake and returns before any actual producer/reader launch.

    def test_modified_pinned_plan_inside_shared_clock_refuses_before_generation_stage(self):
        result,generated,_=self.f.execute(tamper=True)
        generated.assert_not_called();self.assertEqual(result['status'],'failed')
        self.assertTrue(Path(self.f.entry['path']).exists());self.assertFalse(result['formal_permission'])

    def test_real_generate_caller_copies_plan_before_profile_io_and_forwards_same_limits(self):
        g=self.caller();snapshot=copy.deepcopy(g.plan)
        original=whole.generated.validate_runtime_profiles
        def profiles(*args,**kwargs):
            g.plan.clear();return original(*args,**kwargs)
        with patch.object(whole.generated,'validate_runtime_profiles',side_effect=profiles):
            result,calls=g.execute()
        self.assertEqual(calls,['producer','initial-reader']);self.assertEqual(result['status'],'verified')
        self.assertEqual(g.create.call_args.kwargs['pipe_raw_limits'],snapshot['pipe_raw_limits'])
        self.assertEqual(g.create.call_args.kwargs['source_pins'],snapshot['source_pins'])
        self.assertEqual(g.plan,{});self.assertFalse(result['execution_authenticated'])

    def test_invalid_allocation_refuses_real_caller_before_either_supervisor_or_parent(self):
        g=self.caller();g.plan['pipe_raw_limits']['source_blob']['stdout.bin']=1048576
        result,calls=g.execute()
        self.assertEqual(result['status'],'failed');self.assertEqual(calls,[]);g.create.assert_not_called()
        self.assertFalse(result['formal_permission'])


if __name__=='__main__':unittest.main()
