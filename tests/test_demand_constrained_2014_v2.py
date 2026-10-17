import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_constrained_2014_v2 as m
from tests.test_demand_common_residual import full_batch
# Private copy: rebinding m must not redirect the discovered v1 tests to v2.
_spec=importlib.util.spec_from_file_location('_demand_constrained_2014_for_v2',Path(__file__).with_name('test_demand_constrained_2014.py'))
original=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(original)
original.m=m
ReplayIntegrationTests=original.ReplayIntegrationTests

class StopAndPreserveTests(unittest.TestCase):
    def test_missing_model_support_stops_before_solve(self):
        batch=full_batch();batch['rows'].pop()
        with patch.object(m,'solve',side_effect=AssertionError('must not solve')):
            with self.assertRaisesRegex(RuntimeError,'required_model_support_missing'):
                m.train_batch(batch,lambda:None)
    def test_failure_reserve_keeps_partial_predictions(self):
        partial=[{'key':'artificial','candidate_total':'3/2','candidate_daily_exact':['3/28']*14}]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'fresh';files=m.Output(root)
            m.save_failure(files,'artificial-Q2',RuntimeError('artificial-failure'),[{'cutoff':'2014-01-01'}],partial)
            self.assertEqual(json.loads((root/'failure-predictions.json').read_bytes()),partial)
            self.assertTrue(json.loads((root/'failure-progress.json').read_bytes())['later_quarters_and_scoring_stopped'])

if __name__=='__main__':unittest.main()
