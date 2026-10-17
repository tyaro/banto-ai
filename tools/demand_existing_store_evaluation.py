"""One frozen-state Mac evaluation of existing stores in 2015; no fitting."""
import time
STARTED = time.monotonic()
import argparse
import csv
import datetime as dt
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback
import zipfile

from demand_macos_rebuild import HashedReader, PastOnly, ZIP_SHA, eval_metrics, pin, snapshot
from demand_group_selection import FIT, progress
from demand_public_calendar import build_inputs
from demand_statistical_features import encode_profile
from demand_statistical_overlay import describe_history
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin as file_pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-existing-store-evaluation-design-2026-10-15.md'
PURPOSE = 'docs/research/demand-existing-store-purpose-2026-10-15.md'
FIRST, LAST = dt.date(2014, 11, 18), dt.date(2015, 12, 28)
ORIGINS = tuple(dt.date(2015, 1, 13) + dt.timedelta(days=14*k) for k in range(25))
STORE_TEXT = frozenset(map(str, FIT))
METHODS = ('baseline', 'time_selected', 'transfer_selected')
STATE_SHAS = {'time_selected': '166171df43537141ea6174b0180f21e5044ddc54d4ea35c4ea7af5018d05aaf6',
              'transfer_selected': '58fbb3e1cf0684f630e17beb60ad8d546e234ebcba5cf3345a628ed00d275a95'}


def select_row(row):
    # Never convert sales/onpromotion before store/family/date scope acceptance.
    if row['family'] != 'BREAD/BAKERY' or row['store_nbr'] not in STORE_TEXT:
        return None
    if not str(FIRST) <= row['date'] <= str(LAST):
        return None
    store, day, value = int(row['store_nbr']), dt.date.fromisoformat(row['date']), float(row['sales'])
    if not math.isfinite(value) or value < 0:
        raise ValueError('selected finite nonnegative quantity required')
    return store, day, value


def extract(archive, checkpoint):
    histories = {s: {} for s in FIT}
    before = archive.stat()
    count = 0
    with zipfile.ZipFile(archive) as zipped, zipped.open('train.csv') as member:
        hashed = HashedReader(member)
        with io.TextIOWrapper(io.BufferedReader(hashed), encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['id', 'date', 'store_nbr', 'family', 'sales', 'onpromotion']:
                raise ValueError('unexpected source schema')
            for row in reader:
                count += 1
                selected = select_row(row)
                if selected is not None:
                    s, day, value = selected
                    if day in histories[s] or (histories[s] and day <= next(reversed(histories[s]))):
                        raise ValueError('duplicate or unordered selected series')
                    histories[s][day] = value
                if count % 100000 == 0:
                    checkpoint()
    after = archive.stat()
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if stamp(before) != stamp(after) or count != 3000888:
        raise ValueError('archive identity or source row count changed')
    if not all(histories.values()):
        raise ValueError('missing fixed store')
    return histories, {'name': 'train.csv', 'rows': count, 'bytes': hashed.byte_count,
                       'sha256': hashed.digest.hexdigest(), 'selected_stores': list(FIT),
                       'first': str(FIRST), 'last': str(LAST), 'family': 'BREAD/BAKERY',
                       'selected_quantity_rows': sum(map(len, histories.values())),
                       'selection_before_numeric_payload': True, 'promotion_numeric_read': False,
                       'reserved_2016_2017_numeric_read': False}


def assemble(histories, scales, enabled, checkpoint=lambda: None):
    rows, profiles, pending = [], [], []
    for store in FIT:
        for origin in ORIGINS:
            past = PastOnly(histories[store], origin)
            x = build_inputs(past, origin, scales[store], 'pre_post', enabled)
            profile = describe_history(past, origin)
            encoded = encode_profile(profile, origin, scales[store])
            baseline = x['baseline'] if None not in x['baseline'] else None
            rows.append({'store': store, 'origin': str(origin), 'scale': scales[store],
                         'baseline': baseline, 'time_selected': None, 'transfer_selected': None,
                         'model_available': x['available'], 'input_reasons': x['reasons']})
            profiles.append({'store': store, 'origin': str(origin), 'profile': profile, 'encoded': encoded})
            if x['available']:
                pending.append((len(rows)-1, x, encoded))
            checkpoint()
    return rows, profiles, pending


def attach_labels(rows, histories):
    # Keep the saved prediction dicts unchanged and use a separate label path.
    labelled = []
    for row in rows:
        origin = dt.date.fromisoformat(row['origin'])
        actual = [histories[row['store']].get(origin + dt.timedelta(days=k)) for k in range(14)]
        labelled.append({**row, 'actual': actual, 'complete_label': all(a is not None for a in actual)})
    return labelled


def metrics(rows, scales):
    expected = {(s, str(d)) for s in FIT for d in ORIGINS}
    if len(rows) != len(expected) or {(r['store'], r['origin']) for r in rows} != expected:
        raise ValueError('fixed 250-key grid changed')
    for row in rows:
        if row['scale'] != scales[row['store']] or scales[row['store']] <= 0:
            raise ValueError('fixed positive scale changed')
        if (len(row['actual']) != 14 or type(row['complete_label']) is not bool
                or row['complete_label'] != all(a is not None for a in row['actual'])):
            raise ValueError('label mask changed')
        for m in METHODS:
            values = row[m]
            if values is not None and (len(values) != 14 or any(
                    type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values)):
                raise ValueError('invalid saved prediction')
        if any(a is not None and (type(a) not in (int, float) or not math.isfinite(a) or a < 0)
               for a in row['actual']):
            raise ValueError('invalid observed label')
    by_store = {str(s): {m: eval_metrics([r for r in rows if r['store'] == s], scales[s], m)
                        for m in METHODS} for s in FIT}
    def aggregate(selected):
        values = {s: {m: eval_metrics([r for r in selected if r['store'] == s], scales[s], m)
                      for m in METHODS} for s in FIT}
        if any(values[s][m][f] is None for s in FIT for m in METHODS for f in ('daily', 'total', 'joint')):
            raise ValueError('fixed store has no scored support; do not drop or reweight')
        fields = ('daily', 'total', 'joint', 'daily_MAE', 'total_MAE', 'daily_bias', 'total_bias',
                  'daily_WAPE_percent', 'total_WAPE_percent')
        macro = {m: {f: math.fsum(values[s][m][f] for s in FIT)/len(FIT)
                        if all(values[s][m][f] is not None for s in FIT) else None for f in fields} for m in METHODS}
        return macro, {str(s): v for s, v in values.items()}
    measured, _ = aggregate(rows)
    quarters, quarter_stores = {}, {}
    for q in range(1, 5):
        quarters[str(q)], quarter_stores[str(q)] = aggregate(
            [r for r in rows if (dt.date.fromisoformat(r['origin']).month-1)//3+1 == q])
    support = {str(s): {'requested': 25, 'model_available': sum(r['model_available'] for r in rows if r['store'] == s),
                        'complete_labels': sum(r['complete_label'] for r in rows if r['store'] == s),
                        'methods': {m: {'predicted_windows': sum(r[m] is not None for r in rows if r['store'] == s),
                                        'observed_daily_labels': by_store[str(s)][m]['observed_daily_labels'],
                                        'complete_total_labels': by_store[str(s)][m]['complete_total_labels']}
                                    for m in METHODS}} for s in FIT}
    same_support = all((r[m] is None) == (r['baseline'] is None) for r in rows for m in METHODS)
    return {'macro': measured, 'per_store': by_store, 'quarter_macro': quarters,
            'quarter_per_store': quarter_stores, 'macro_weighting': 'equal_fixed_10_stores_including_MAE_WAPE_bias',
            'support_counts': support,
            'primary_development_decision': progress(measured['time_selected'], measured['baseline'], same_support),
            'improved_stores': {m: sum(by_store[str(s)][m]['joint'] < by_store[str(s)]['baseline']['joint'] for s in FIT)
                                for m in METHODS[1:]},
            'requested': len(rows), 'neural_supported': sum(r['model_available'] for r in rows),
            'complete_label_windows': sum(r['complete_label'] for r in rows)}


def run(output, archive):
    import torch
    from demand_statistical_feature_model import StatisticalFeatureMean
    from demand_calendar_train import Files
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh local output root required')
    files = Files(root)
    guard = MacCheckpoint(seconds=870)
    status, stage, rows = 'failed', 'source', []
    source_root = REPO/'artifacts/macos-demand-rebuild-20261015'
    try:
        if sys.version_info[:3] != (3, 14, 8) or torch.__version__ != '2.14.0' or sys.platform != 'darwin':
            raise ValueError('fixed Mac Python3.14.8/Torch2.14.0 required')
        original = verify(source_root)
        if original['recorded_status'] != 'complete':
            raise ValueError('complete original model root required')
        prior = json.loads((source_root/'summary.json').read_bytes())
        for name, expected in prior['source_pins'].items():
            if file_pin(REPO/name) != expected:
                raise ValueError('original source pin changed: '+name)
        source_paths = [CONTRACT, PURPOSE, 'tools/demand_existing_store_evaluation.py',
                        'tools/verify_demand_transfer.py', 'tools/verification_records.py', *prior['source_pins']]
        sources = {p: (REPO/p).read_bytes() for p in dict.fromkeys(source_paths)}
        files.write('contract.md', sources[CONTRACT])
        files.json('sources.json', {p: raw.decode() for p, raw in sources.items()})
        archive_pin = file_pin(archive)
        if archive_pin != {'bytes': 22416355, 'sha256': ZIP_SHA}:
            raise ValueError('fixed archive pin mismatch')
        scale_meta = json.loads((source_root/'scale-metadata.json').read_bytes())
        scales = {s: scale_meta[str(s)]['scale'] for s in FIT}
        if not all(math.isfinite(scales[s]) and scales[s] > 0 and
                   scale_meta[str(s)]['cutoff_exclusive'] == '2014-07-01' for s in FIT):
            raise ValueError('fixed positive preperiod scales required')
        support = json.loads((source_root/'split-support.json').read_bytes())['support']
        if len(support['enabled']) != 56 or sum(support['enabled']) != 42 or support['keys'] != 300:
            raise ValueError('fixed fit calendar support changed')
        files.json('scale-and-calendar-binding.json', {'scales': {str(s): scale_meta[str(s)] for s in FIT},
                   'calendar_support': support, 'source_closure': original})
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        models, state_pins = {}, {}
        for name, sha in STATE_SHAS.items():
            path = source_root/(name+'.pt')
            state_pins[name] = file_pin(path)
            if state_pins[name]['sha256'] != sha:
                raise ValueError('frozen state pin mismatch: '+name)
            state = torch.load(path, weights_only=True, map_location='cpu')
            clone = StatisticalFeatureMean(); clone.load_state_dict(state, strict=True); clone.eval()
            if (sum(p.numel() for p in clone.parameters()) != 30369 or
                    any(p.device.type != 'cpu' or p.dtype != torch.float32 or not bool(torch.isfinite(p).all())
                        for p in clone.parameters())):
                raise ValueError('fixed model dtype/device/shape changed')
            models[name] = clone
        files.json('frozen-selections-before-input.json', {'primary': 'time_selected', 'primary_step': 3328,
                   'secondary': 'transfer_selected', 'secondary_step': 3072, 'weight_pins': state_pins,
                   'original_trajectory_stopped_by': 'C_transfer_validation', 'new_fit': False,
                   'no_further_weight_selection': True, 'target_quantity_interpreted': False})
        files.json('config-before-input.json', {'archive': archive_pin, 'stores': list(FIT), 'family': 'BREAD/BAKERY',
                   'origins': list(map(str, ORIGINS)), 'first': str(FIRST), 'last': str(LAST),
                   'primary': 'time_selected', 'source_pins': {p: pin(raw) for p, raw in sources.items()},
                   'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                   'runtime': {'python': sys.version, 'torch': torch.__version__, 'device': 'cpu', 'dtype': 'float32',
                               'threads': 2, 'interop_threads': 1, 'deterministic': True},
                   'formal_permission': False})
        guard.check(); stage = 'selected-source-extraction'
        histories, member_pin = extract(archive, guard.check)
        if {k: member_pin[k] for k in ('bytes', 'rows', 'sha256')} != {
                k: prior['train_member_pin'][k] for k in ('bytes', 'rows', 'sha256')}:
            raise ValueError('original train member pin mismatch')
        files.json('source-manifest.json', {'archive_path': str(archive), 'archive_pin': archive_pin,
                                         'train_member_pin': member_pin})
        files.write('selected-existing-stores.csv', snapshot(histories, FIRST, LAST))
        stage = 'past-only-inputs'
        rows, profiles, pending = assemble(histories, scales, support['enabled'], guard.check)
        files.json('existing-store-profiles.json', profiles)
        fields = ('normalized_values', 'observed', 'past_calendar', 'future_calendar',
                  'context_statistics', 'baseline', 'scale')
        stage = 'frozen-forward'
        with torch.no_grad():
            for start in range(0, len(pending), 8):
                batch = pending[start:start+8]
                inputs = [torch.tensor([r[1][f] for r in batch], dtype=torch.bool if f == 'observed' else torch.float32)
                          for f in fields]
                inputs.append(torch.tensor([r[2]['features'] for r in batch], dtype=torch.float32))
                for name, model in models.items():
                    daily, total = model(*inputs)
                    for j, (index, _, _) in enumerate(batch):
                        values = daily[j].tolist()
                        if not math.isclose(math.fsum(values), total[j].item(), rel_tol=1e-6, abs_tol=1e-5):
                            raise ValueError('daily/total inconsistency')
                        rows[index][name] = values
                guard.check()
        files.json('predictions-before-labels.json', rows)
        stage = 'label-attachment'
        labelled = attach_labels(rows, histories)
        files.json('predictions-and-labels.json', labelled)
        if rows != [{k: v for k, v in r.items() if k not in ('actual', 'complete_label')} for r in labelled]:
            raise ValueError('prediction changed during label attachment')
        stage = 'fixed-metrics'
        result = metrics(labelled, scales)
        if any((REPO/p).read_bytes() != raw for p, raw in sources.items()) or verify(source_root) != original:
            raise ValueError('original root or pinned source changed')
        if file_pin(archive) != archive_pin:
            raise ValueError('archive changed during evaluation')
        summary = {'status': 'complete', 'research_state': 'PAUSED', 'primary': 'time_selected',
                   'secondary': 'transfer_selected', 'weight_pins': state_pins, 'source': original,
                   'source_pins': {p: pin(raw) for p, raw in sources.items()}, 'archive_pin': archive_pin,
                   'train_member_pin': member_pin, 'calendar_enabled_channels': 42, 'new_profiles': len(profiles),
                   'parameter_count': 30369, 'new_fit': False, 'new_weight_selection': False,
                   'unique_forward_states': 2, 'original_root_unchanged': True, 'formal_permission': False,
                   'adopted': False, 'evaluation_role': 'retrospective_existing_store_development',
                   'resources': guard.check(), 'seconds': time.monotonic()-STARTED, **result}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({k: summary[k] for k in ('status', 'primary', 'macro', 'primary_development_decision',
                                                'improved_stores', 'requested', 'neural_supported',
                                                'complete_label_windows', 'seconds')}, sort_keys=True), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error),
                                  'traceback': traceback.format_exc(), 'research_state': 'PAUSED'}, True)
        files.json('failure-prefix.json', {'rows': rows}, True)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True,
                                     'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    run(args.output, args.archive)
