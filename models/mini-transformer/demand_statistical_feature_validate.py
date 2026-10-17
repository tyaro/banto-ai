"""One later-time evaluation of two frozen states, with no training or selection."""
import time
STARTED = time.monotonic()
from pathlib import Path
import argparse, csv, datetime as dt, hashlib, io, json, math, sys, traceback, zipfile
import torch
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
from verification_records import verify_record
from store_sales_final import private_memory
from demand_statistical_feature_model import StatisticalFeatureMean
from demand_statistical_feature_train import model_inputs, without_features
from demand_calendar_train import Files, pin, error_metrics, item
from demand_public_calendar import build_inputs
from demand_statistical_overlay import describe_history
from demand_statistical_features import encode_profile


class HashedReader(io.RawIOBase):
    def __init__(self, raw):
        self.raw, self.digest, self.byte_count = raw, hashlib.sha256(), 0
    def readable(self): return True
    def readinto(self, buffer):
        raw = self.raw.read(len(buffer)); buffer[:len(raw)] = raw
        self.digest.update(raw); self.byte_count += len(raw)
        return len(raw)


class AsOfHistory:
    def __init__(self, history, origin):
        self.history, self.origin, self.accessed = history, origin, []
    def get(self, day):
        if not self.origin - dt.timedelta(days=56) <= day < self.origin:
            raise ValueError('input getter outside completed 56-day prefix')
        self.accessed.append(str(day)); return self.history.get(day)


def run(output):
    root = Path(output).absolute()
    if root.parent != REPO / 'artifacts' or root.exists(): raise ValueError('fresh output root required')
    files = Files(root); status, stage, peak = 'failed', 'contract', 0
    selected, rows, profiles = [], [], []
    def checkpoint():
        nonlocal peak
        peak = max(peak, private_memory())
        if peak > 2 * 1024**3 or time.monotonic() - STARTED > 870:
            raise RuntimeError('execution checkpoint; preserve and stop')
    try:
        cr = REPO / 'artifacts/representative-demand-stat-validation-contract-20261014-records'
        assert verify_record(cr)['status'] == 'complete'
        contract_raw = item(cr, 'frozen-before-quantity'); contract = json.loads(contract_raw)
        assert not contract['new_target_quantity_read'] and not contract['formal_permission']
        active, zero, stores = contract['active'], contract['baseline_only'], contract['stores']
        dates = [dt.date.fromisoformat(d) for d in contract['origins']]
        assert active == [6,7,9,10,13,14,15,17,18,19,23,25,26,27,30] and zero == [21,22,29]
        assert stores == sorted(active + zero) and dates == [dt.date(2016,1,13) + dt.timedelta(days=14*k) for k in range(25)]
        pair = REPO / 'artifacts/representative-demand-stat-feature-pair-20261014'
        closure_raw = (pair / 'root-closed.json').read_bytes()
        assert pin(closure_raw) == contract['model_closure_pin'] and json.loads(closure_raw)['status'] == 'complete'
        frozen = {}
        for name, expected in contract['frozen_files'].items():
            raw = (pair / name).read_bytes(); assert pin(raw) == expected; frozen[name] = raw
        source_paths = list(contract['model_source_pins']) + [
            'models/mini-transformer/demand_statistical_feature_validate.py',
            'docs/research/demand-statistical-feature-validation-design-2026-10-14.md']
        sources = {p: (REPO / p).read_bytes() for p in source_paths}
        for path, expected in contract['model_source_pins'].items(): assert pin(sources[path]) == expected
        files.write('contract.json', contract_raw)
        files.json('sources.json', {p: r.decode('utf-8') for p, r in sources.items()})
        files.json('frozen-before-quantity.json', {'contract_pin': pin(contract_raw),
          'contract_closure_pin': pin((cr / 'root-closed.json').read_bytes()), 'weight_pins': contract['model_weight_pins'],
          'source_pins': {p: pin(r) for p, r in sources.items()}, 'new_training': False,
          'compute_parent_head': '601c06bce46c967ddbc5587dab09dd6950bc97d0',
          'uncommitted_validation_source': True, 'python': sys.version, 'torch': torch.__version__})
        binding = json.loads(frozen['binding.json']); scales = {int(s): v for s, v in binding['scales'].items()}
        assert all(scales[s] > 0 for s in active) and all(scales[s] == 0 for s in zero)
        prior = REPO / 'artifacts/representative-demand-public-calendar-input-20261014-records'
        support_raw = item(prior, 'fit-support'); support = json.loads(support_raw)
        assert pin(support_raw) == binding['support_pin'] and sum(support['enabled']) == 42
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        models = {}
        for method in ('feature_off', 'feature_on'):
            model = StatisticalFeatureMean()
            state = torch.load(io.BytesIO(frozen[method + '-final.pt']), map_location='cpu', weights_only=True)
            model.load_state_dict(state)
            assert all(torch.equal(v, state[k]) for k,v in model.state_dict().items())
            model.eval(); models[method] = model
        checkpoint(); stage = 'prefix-and-extraction'
        wanted = {d + dt.timedelta(days=k) for d in dates for k in range(-56,14)}
        prefix_root = REPO / 'artifacts/representative-store-sales-shared-prefix-20261014-records'
        assert verify_record(prefix_root)['status'] == 'complete'
        prefix_raw = item(prefix_root, 'selected-quantity-csv'); assert pin(prefix_raw) == contract['prefix_snapshot_pin']
        histories, originals = {s:{} for s in stores}, {}
        for row in csv.DictReader(io.StringIO(prefix_raw.decode())):
            s, day = int(row['store_nbr']), dt.date.fromisoformat(row['date'])
            if s not in stores or day not in wanted or day.year != 2015: continue
            assert day not in histories[s] and row['observed'] in ('0','1')
            assert (row['observed'] == '1') == bool(row['sales'])
            histories[s][day] = float(row['sales']) if row['observed'] == '1' else None
            originals[s,day] = row
        prefix_wanted = {day for day in wanted if day.year == 2015}
        assert all(set(history) == prefix_wanted for history in histories.values())
        source = REPO / 'data/public/store-sales-user-provided-20261014'
        manifest_raw = (source / 'source-manifest.json').read_bytes(); manifest = json.loads(manifest_raw)
        assert manifest['archive'] == contract['archive_pin']
        member = next(m for m in manifest['members'] if m['name'] == 'train.csv')
        assert {k: member[k] for k in ('bytes','rows','sha256')} == contract['member_pin']
        archive = source / manifest['archive']['filename']; before = archive.stat()
        assert archive.is_file() and not archive.is_symlink()
        digest = hashlib.sha256()
        with archive.open('rb') as stream:
            while raw := stream.read(256 * 1024): digest.update(raw); checkpoint()
        assert before.st_size == contract['archive_pin']['bytes'] and digest.hexdigest() == contract['archive_pin']['sha256']
        count, order = 0, {}; store_text = {str(s) for s in stores}
        with zipfile.ZipFile(archive) as z, z.open('train.csv') as original:
            hashed = HashedReader(original)
            with io.TextIOWrapper(io.BufferedReader(hashed), encoding='utf-8', newline='') as stream:
                reader = csv.DictReader(stream)
                assert reader.fieldnames == ['id','date','store_nbr','family','sales','onpromotion']
                for row in reader:
                    count += 1
                    if count % 100000 == 0: checkpoint()
                    if row['store_nbr'] not in store_text or row['family'] != contract['family']: continue
                    day = dt.date.fromisoformat(row['date'])
                    if day.year != 2016 or day not in wanted: continue
                    s, value = int(row['store_nbr']), float(row['sales'])
                    assert math.isfinite(value) and value >= 0 and day not in histories[s]
                    assert s not in order or order[s] < day
                    order[s] = day; histories[s][day] = value
                    entry = {'store_nbr':str(s), 'date':str(day), 'source_id':row['id'], 'sales':row['sales'], 'observed':'1'}
                    originals[s,day] = entry; selected.append(entry)
        assert hashed.byte_count == member['bytes'] and hashed.digest.hexdigest() == member['sha256'] and count == member['rows']
        after = archive.stat()
        assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) == (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
        snapshot = io.StringIO(); writer = csv.DictWriter(snapshot, ['store_nbr','date','source_id','sales','observed']); writer.writeheader()
        for s in stores:
            for day in sorted(wanted):
                if day not in histories[s]: histories[s][day] = None
                writer.writerow(originals.get((s,day), {'store_nbr':str(s),'date':str(day),'source_id':'','sales':'','observed':'0'}))
            assert set(histories[s]) == wanted
        snapshot_raw = snapshot.getvalue().encode(); files.write('selected-quantity.csv', snapshot_raw)
        files.json('input-binding.json', {'archive': contract['archive_pin'], 'member': contract['member_pin'],
          'manifest_pin': pin(manifest_raw), 'archive_identity_before_after': list((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)),
          'archive_unchanged': True, 'prefix_pin': pin(prefix_raw), 'snapshot_pin': pin(snapshot_raw),
          'new_2016_observed_rows': len(selected), 'calendar_rows': len(stores)*len(wanted),
          'support_pin': pin(support_raw), 'scales': scales, '2017_reserved_other_store_promotion_numeric_read': False})
        stage = 'new-inputs-and-frozen-inference'; pending = []
        for s in stores:
            for origin in dates:
                past = AsOfHistory(histories[s], origin)
                x = build_inputs(past, origin, scales[s], 'pre_post', support['enabled'])
                profile = describe_history(past, origin); encoded = encode_profile(profile, origin, scales[s])
                profiles.append({'store':s,'origin':str(origin),'profile':profile,'encoded':encoded,
                                 'accessed_count':len(past.accessed),'accessed_min':min(past.accessed),'accessed_max':max(past.accessed)})
                baseline = x['baseline'] if None not in x['baseline'] else None
                row = {'store':s, 'origin':str(origin), 'scale':scales[s], 'baseline':baseline,
                  'feature_off':baseline if s in zero else None, 'feature_on':baseline if s in zero else None,
                  'model_available':x['available'], 'input_reasons':x['reasons'],
                  'role':'positive_scale' if s in active else 'zero_scale_baseline_only'}
                rows.append(row)
                if s in active and x['available']: pending.append((len(rows)-1,x,encoded))
        files.json('new-origin-profiles.json', profiles)
        with torch.no_grad():
            for start in range(0,len(pending),8):
                batch = pending[start:start+8]
                full = model_inputs([x for i,x,e in batch],[e for i,x,e in batch]); control = without_features(full)
                for method,data in (('feature_off',control),('feature_on',full)):
                    daily,total = models[method](*data)
                    for j,(index,x,e) in enumerate(batch):
                        values = daily[j].tolist()
                        assert math.isclose(math.fsum(values),total[j].item(),rel_tol=1e-6,abs_tol=1e-5)
                        rows[index][method] = values
                checkpoint()
        files.json('predictions-before-labels.json', rows)
        stage = 'attach-labels-after-prediction-save'
        for row in rows:
            origin = dt.date.fromisoformat(row['origin'])
            row['actual'] = [histories[row['store']].get(origin+dt.timedelta(days=k)) for k in range(14)]
            row['complete_label'] = all(v is not None for v in row['actual'])
            row['comparable'] = all(row[m] is not None for m in ('baseline','feature_off','feature_on'))
        files.json('predictions-and-labels.json', rows)
        stage = 'new-validation-metrics'; methods = ('baseline','feature_off','feature_on')
        def metrics(rs,u=None):
            result = {}
            for method in methods:
                de,da,te,ta = [],[],[],[]
                for r in rs:
                    if not r['comparable']: continue
                    for p,a in zip(r[method],r['actual']):
                        if a is not None: de.append(p-a); da.append(a)
                    if r['complete_label']:
                        te.append(math.fsum(r[method])-math.fsum(r['actual'])); ta.append(math.fsum(r['actual']))
                result[method] = {'daily':error_metrics(de,da,[u]*len(de) if u else None),
                  'total':error_metrics(te,ta,[14*u]*len(te) if u else None)}
            return result
        by_store = {str(s):metrics([r for r in rows if r['store']==s],scales[s]) for s in stores}
        support_counts = {str(s):{'requested':25,'model_and_baseline':sum(r['comparable'] for r in rows if r['store']==s),
          'complete_comparable_labels':sum(r['comparable'] and r['complete_label'] for r in rows if r['store']==s)} for s in active}
        minimum = contract['readiness_min_model_and_complete_windows_each_positive_store']
        readiness = all(v['model_and_baseline']>=minimum and v['complete_comparable_labels']>=minimum for v in support_counts.values())
        store_joint = {str(s):{m:.5*sum(by_store[str(s)][m][scope]['scaled_MSE'] for scope in ('daily','total'))
                               if all(by_store[str(s)][m][scope]['scaled_MSE'] is not None for scope in ('daily','total')) else None
                               for m in methods} for s in active}
        primary = {m:math.fsum(store_joint[str(s)][m] for s in active)/len(active)
                   if all(store_joint[str(s)][m] is not None for s in active) else None for m in methods}
        secondary = {scope:{m:math.fsum(by_store[str(s)][m][scope]['scaled_MSE'] for s in active)/len(active)
                          if all(by_store[str(s)][m][scope]['scaled_MSE'] is not None for s in active) else None
                          for m in methods} for scope in ('daily','total')}
        improved = [s for s in active if all(v is not None for v in store_joint[str(s)].values())
                    and all(store_joint[str(s)]['feature_on']<store_joint[str(s)][m] for m in methods[:2])]
        progress = readiness and all(v is not None for v in primary.values()) and all(primary['feature_on']<primary[m] for m in methods[:2]) and len(improved)>=10
        origin_groups = {str(d):metrics([r for r in rows if r['origin']==str(d) and r['store'] in active]) for d in dates}
        quarters = {str(q):metrics([r for r in rows if r['store'] in active and (dt.date.fromisoformat(r['origin']).month-1)//3+1==q]) for q in range(1,5)}
        # Descriptive origin/quarter differences retain each store's fixed scale.
        def scaled_group(rs):
            ms = {str(s):metrics([r for r in rs if r['store']==s],scales[s]) for s in active}
            return {m:.5*math.fsum(sum(ms[str(s)][m][scope]['scaled_MSE'] for scope in ('daily','total')) for s in active)/len(active)
                      if all(ms[str(s)][m][scope]['scaled_MSE'] is not None for s in active for scope in ('daily','total')) else None for m in methods}
        quarter_joint = {str(q):scaled_group([r for r in rows if (dt.date.fromisoformat(r['origin']).month-1)//3+1==q]) for q in range(1,5)}
        origin_joint = {str(d):scaled_group([r for r in rows if r['origin']==str(d)]) for d in dates}
        zero_diagnostics = {str(s):{'windows':25,'positive_observed_targets':sum(a is not None and a>0 for r in rows if r['store']==s for a in r['actual']),
                                 'missing_targets':sum(a is None for r in rows if r['store']==s for a in r['actual'])} for s in zero}
        for name,expected in contract['frozen_files'].items(): assert pin((pair/name).read_bytes())==expected
        assert all((REPO/path).read_bytes()==raw for path,raw in sources.items()); checkpoint()
        result = {'status':'complete','research_state':'ACTIVE' if progress else 'PAUSED','progress_passed':bool(progress),
          'readiness_passed':readiness,'adopted':False,'primary_joint_macro_scaled_MSE':primary,
          'secondary_macro_scaled_MSE':secondary,'per_store':by_store,'store_joint_MSE':store_joint,
          'improved_stores':improved,'support_counts':support_counts,'origin_raw_metrics':origin_groups,
          'quarter_raw_metrics':quarters,'quarter_joint_MSE':quarter_joint,'origin_joint_MSE':origin_joint,
          'zero_scale_diagnostics':zero_diagnostics,'requested':len(rows),'model_supported':len(pending),
          'complete_label_windows':sum(r['complete_label'] for r in rows),'baseline_only_windows':sum(r['store'] in zero for r in rows),
          'new_observed_2016_rows':len(selected),'new_origin_profiles':len(profiles),'new_training':False,
          'source_pins':{p:pin(raw) for p,raw in sources.items()},'contract_pin':pin(contract_raw),'weight_pins':contract['model_weight_pins'],
          'seconds':time.monotonic()-STARTED,'OS_peak_private_bytes':peak,'formal_permission':False,
          '2017_reserved_registered_holdout_read':False,'same_public_dataset_later_time':True,'no_grid_or_retraining':True}
        files.json('summary.json',result); status='complete'
        print(json.dumps({k:result[k] for k in ('status','research_state','progress_passed','readiness_passed','primary_joint_macro_scaled_MSE','improved_stores','requested','model_supported','seconds','OS_peak_private_bytes')}),flush=True)
    except BaseException as error:
        original=traceback.format_exc()
        try:
            files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':original,'research_state':'PAUSED'},True)
            if selected:files.json('failure-extraction-prefix.json',selected,True)
            if rows:files.json('failure-prediction-prefix.json',rows,True)
        except BaseException as save_error: print('failure save error: '+repr(save_error),file=sys.stderr)
        raise
    finally:
        files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True},status!='complete')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
