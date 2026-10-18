"""CARE practical evaluation: zero-shot foundation-model inference, then freeze before labels.

Conditions: examples/configs/care-a-maintenance-practical-20261017.json, which inherits every
alarm rule of CARE-A-MAINT-20261016-r1. No labels are read here.

    unit      one fixed 1000-origin chunk of one method/fold/segment, run in that model's venv;
              contexts only through care_input.Consumer (past-only); a row-level ValueError
              from the adapter makes that row unsupported, any other failure stops
    campaign  every unit, at most 3 processes at a time, 870 s and the memory limit per unit,
              resumable from closed chunks, 24 h cap (run with any Python; no Torch needed)
    freeze    assemble the chunks with missing/duplicate checks, scores with the fold's saved
              R, per-method 99.5% thresholds and alarm episodes over whole files (never per
              chunk), then hash everything; still no labels

    python3 tools/care_fm.py campaign --output artifacts/care-fm-20261017 --venvs <dir with fm-<method>/>
    python3 tools/care_fm.py freeze --output artifacts/care-fm-20261017
"""
import argparse
import hashlib
import json
import math
import os
import signal
import struct
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# tools/ stays off the path (Python puts a script's directory first): tools/toto2 and
# tools/timesfm3 would shadow the installed toto2 and timesfm3 packages.
sys.path = [p for p in sys.path if Path(p or '.').resolve() != Path(__file__).resolve().parent]
sys.path[:0] = [str(ROOT/'models/mini-transformer'), str(ROOT/'src'), str(ROOT)]
from care_alarm import COMMON, PREDICTION, calibration_threshold, episodes  # noqa: E402

CONTRACT = ROOT/'examples/configs/care-a-maintenance-practical-20261017.json'
DATASET = ROOT/'artifacts/care-numeric-input-20261016'
METHODS = ('timesfm3', 'chronos2', 'toto2')  # scheduled longest first
MEMORY = {'timesfm3': 4 << 30, 'chronos2': 2 << 30, 'toto2': 2 << 30}
SEGMENTS = ('calibration', 'test')
CHUNK = 1000
FOLDS = range(5)
PRED = struct.Struct('<IIdd')  # event, origin n, p50 of the two temperatures (NaN if unsupported)
EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
UNSUPPORTED_STOP = 0.01


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else Path(data).read_bytes()).hexdigest()


def write_new(path, data):
    with open(path, 'xb') as f:
        f.write(data if isinstance(data, bytes) else json.dumps(data, indent=1).encode())


def close(root):
    files = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} if p.is_file()
             else {'name': p.name+'/', 'root_closed_sha256': digest(p/'root-closed.json')}
             for p in sorted(root.iterdir()) if p.name != 'root-closed.json']
    write_new(root/'root-closed.json', {'status': 'complete', 'files': files})


def fold_root(fold):
    return ROOT/f'artifacts/care-learning-fold-{fold}-20261016'


def saved_rows(fold, segment):
    """The saved rows this segment forecasts: every calibration row, the common-support test rows."""
    rows = list(PREDICTION.iter_unpack((fold_root(fold)/f'{segment}.bin').read_bytes()))
    return rows if segment == 'calibration' else [r for r in rows if r[5] & COMMON]


def chunks(fold, segment):
    rows = saved_rows(fold, segment)
    return [rows[i:i+CHUNK] for i in range(0, len(rows), CHUNK)]


def unit_dir(out, method, fold, segment, chunk):
    return Path(out)/method/f'fold-{fold}'/segment/f'chunk-{chunk:04d}'


# ---------------------------------------------------------------- unit (model venv)

def adapter(method, cache):
    """The existing adapter with the contract's settings, offline from the pinned cache."""
    if method == 'chronos2':
        from tools.chronos2 import load_manifest, cache_environment, offline_environment
        from banto_ai.adapters.chronos2 import Chronos2Adapter as A, Chronos2Config as C
        config = C(cache_dir=str(cache), device_map='cpu', local_files_only=True, batch_size=1, context_length=128, cross_learning=False)
    elif method == 'toto2':
        from tools.toto2 import load_manifest, cache_environment, offline_environment
        from banto_ai.adapters.toto2 import Toto2Adapter as A, Toto2Config as C
        config = C(cache_dir=str(cache), device='cpu', batch_size=1, local_files_only=True, patch_size=32)
    else:
        from tools.timesfm3.run_smoke import load_json as load_manifest, _cache_environment as cache_environment, _offline_environment as offline_environment
        from banto_ai.adapters.timesfm3 import TimesFM3Adapter as A, TimesFM3Config as C
        config = C(device='cpu', local_files_only=True, cache_dir=str(cache))
    manifest = load_manifest(ROOT/'examples/manifests'/f'model-license-{method}.json')
    return A, config, manifest, cache_environment(cache), offline_environment()


def request(context, names):
    """Two temperatures as targets, power as a past-only covariate; timestamps are an inert
    fixed epoch plus the file-local record times (600 s apart, ending one interval before issue)."""
    from banto_ai.types import ForecastRequest, QualityStatus, SignalMetadata, SignalPoint, TimeSeries
    first = context.issue_offset_seconds-600*128

    def series(v, role):
        meta = SignalMetadata(names[v], names[v], 'native', 600000, role=role)
        return TimeSeries(meta, tuple(SignalPoint(EPOCH+timedelta(seconds=first+600*j), float(x), QualityStatus.OK)
                                      for j, x in enumerate(context.channels[v])))
    return ForecastRequest(contexts=(series(0, 'target'), series(1, 'target'), series(2, 'covariate')),
                           target_signal_ids=(names[0], names[1]), horizon=1, quantiles=(0.5,))


def run_unit(method, fold, segment, chunk, out, cache):
    import resource
    import torch
    from care_input import Consumer, pinned_input
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    started = time.monotonic(); target = unit_dir(out, method, fold, segment, chunk); target.mkdir(parents=True)
    rows = chunks(fold, segment)[chunk]
    names = pinned_input()['model_feature_order']
    consumer = Consumer(DATASET, fold, segment)
    A, config, manifest, cache_env, offline_env = adapter(method, cache)
    payload = bytearray(); unsupported = []
    with cache_env, offline_env:
        model = A(manifest, config)
        for r in rows:
            event, n, issue = r[0], r[1], r[3]
            context = consumer.context(event, n, issue)  # a failure here is the harness's, not the row's
            try:
                result = model.forecast(request(context, names))
                p50 = {f.signal_id: [q.values[0] for q in f.quantile_forecasts if q.quantile == 0.5][0] for f in result.forecasts}
                values = (p50[names[0]], p50[names[1]])
                if not all(math.isfinite(x) for x in values):
                    raise ValueError('nonfinite p50')
            except ValueError as error:
                unsupported.append({'event': event, 'origin': n, 'error': str(error)[:300]}); values = (math.nan, math.nan)
            payload += PRED.pack(event, n, *values)
    write_new(target/'predictions.bin', bytes(payload))
    write_new(target/'unit.json', {
        'method': method, 'fold': fold, 'segment': segment, 'chunk': chunk, 'rows': len(rows),
        'first_origin': [rows[0][0], rows[0][1]], 'last_origin': [rows[-1][0], rows[-1][1]],
        'unsupported': unsupported, 'seconds': time.monotonic()-started,
        'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'fold_root_closure_sha256': digest(fold_root(fold)/'root-closed.json'),
        'dataset_closure_sha256': digest(DATASET/'root-closed.json'), 'torch': torch.__version__,
        'checkpoint_revision': getattr(config, 'checkpoint_revision', None), 'harness_sha256': digest(Path(__file__))})
    close(target)


# ---------------------------------------------------------------- campaign (any Python)

def campaign(out, venvs, parallel, hours):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    log = out/'campaign-log.jsonl'; deadline = time.monotonic()+hours*3600
    todo = [(m, k, s, c) for m in METHODS for k in FOLDS for s in SEGMENTS for c in range(len(chunks(k, s)))]
    pending = []
    for unit in todo:
        d = unit_dir(out, *unit)
        if (d/'root-closed.json').exists():
            continue
        if d.exists():  # an unclosed chunk from a stopped run is never reused
            stale = d.with_name(d.name+f'.incomplete-{int(time.time())}'); d.rename(stale)
            record(log, {'event': 'incomplete-chunk-set-aside', 'unit': unit, 'moved_to': str(stale)})
        pending.append(unit)
    record(log, {'event': 'start', 'pending': len(pending), 'total': len(todo), 'harness_sha256': digest(Path(__file__))})
    running = {}
    while pending or running:
        while pending and len(running) < parallel:
            unit = pending.pop(0); m = unit[0]
            cmd = [str(Path(venvs)/f'fm-{m}'/'bin/python'), str(Path(__file__)), 'unit', '--method', m, '--fold', str(unit[1]),
                   '--segment', unit[2], '--chunk', str(unit[3]), '--output', str(out), '--cache', str(Path(venvs)/'hf-cache'/m)]
            (out/'logs').mkdir(exist_ok=True)
            err = open(out/'logs'/('-'.join(map(str, unit))+f'.{int(time.time())}.stderr'), 'w')
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=err, start_new_session=True)
            err.close(); running[proc] = (unit, time.monotonic(), err.name)
        time.sleep(1)
        for proc, (unit, began, errname) in list(running.items()):
            if proc.poll() is None and time.monotonic()-began <= 870 and time.monotonic() < deadline:
                continue
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                stop(log, running, {'event': 'stop', 'reason': 'unit over 870 s or campaign over the cap', 'unit': unit})
            del running[proc]
            stderr = Path(errname).read_text(errors='replace')
            if proc.returncode != 0:
                stop(log, running, {'event': 'stop', 'reason': 'unit failed', 'unit': unit, 'stderr': stderr[-3000:]})
            info = json.loads((unit_dir(out, *unit)/'unit.json').read_bytes())
            if info['peak_rss_bytes'] > MEMORY[unit[0]]:
                stop(log, running, {'event': 'stop', 'reason': 'memory limit', 'unit': unit, 'peak_rss_bytes': info['peak_rss_bytes']})
            record(log, {'event': 'unit-done', 'unit': unit, 'seconds': round(info['seconds'], 1),
                         'peak_rss_bytes': info['peak_rss_bytes'], 'unsupported': len(info['unsupported'])})
    record(log, {'event': 'complete'})


def record(log, entry):
    with open(log, 'a') as f:
        f.write(json.dumps({'time': datetime.now(timezone.utc).isoformat(), **entry})+'\n')


def stop(log, running, entry):
    for proc in running:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL); proc.wait()
    record(log, entry)
    raise SystemExit(json.dumps(entry)[:3000])


# ---------------------------------------------------------------- freeze (any Python)

def assemble(expected, chunk_payloads):
    """Predictions keyed by (event, origin); every expected row exactly once, nothing else."""
    out = {}
    for payload in chunk_payloads:
        for event, n, a, b in PRED.iter_unpack(payload):
            if (event, n) in out:
                raise ValueError(f'duplicate prediction for {(event, n)}')
            out[(event, n)] = (a, b)
    keys = [(r[0], r[1]) for r in expected]
    missing = [k for k in keys if k not in out]
    if missing or len(out) != len(keys):
        raise ValueError(f'prediction rows differ from the saved rows: {len(missing)} missing, {len(out)-len(keys)+len(missing)} extra')
    return out


def score(row, p50, R):
    """Inherited score on the saved observed temperatures: max over the two of |y - p50| / R."""
    return max(abs(row[6+v]-p50[v])/R[v] for v in range(2))


def method_rows(saved, predictions, R):
    """Saved test rows in the r1 layout with this method's p50 and score in the model slots
    (the own model's quantile slots become NaN); COMMON only where the method forecast the row,
    so an unsupported row is the inherited gap. Observations and baseline slots are kept."""
    rows = []
    for r in saved:
        p = predictions.get((r[0], r[1]))
        ok = bool(r[5] & COMMON) and p is not None and all(math.isfinite(x) for x in p)
        p50 = p if ok else (math.nan, math.nan)
        rows.append((*r[:5], COMMON if ok else 0, r[6], r[7], *p50, r[10], r[11],
                     score(r, p, R) if ok else math.nan, r[13], *[math.nan]*9))
    return rows


def episodes_by_event(rows, threshold):
    """Alarm episodes per event file over the whole file in order (chunk boundaries do not exist here)."""
    out = {}
    for event in sorted({r[0] for r in rows}):
        out[event] = episodes([r for r in rows if r[0] == event], 'neural-common', threshold)
    return out


def freeze(out):
    out = Path(out); frozen = out/'frozen'; frozen.mkdir()
    summary = {'methods': {}, 'labels_read': False}
    for m in METHODS:
        per = {}
        for k in FOLDS:
            R = [v['R64'] for v in json.loads((fold_root(k)/'input.json').read_bytes())['profile']['alarm_scales']]
            loaded = {}
            for s in SEGMENTS:
                dirs = [unit_dir(out, m, k, s, c) for c in range(len(chunks(k, s)))]
                for d in dirs:
                    if not (d/'root-closed.json').exists():
                        raise ValueError(f'unit not closed: {d}')
                loaded[s] = assemble(saved_rows(k, s), [(d/'predictions.bin').read_bytes() for d in dirs])
            calibration = [score(r, loaded['calibration'][(r[0], r[1])], R) for r in saved_rows(k, 'calibration')
                           if all(math.isfinite(x) for x in loaded['calibration'][(r[0], r[1])])]
            threshold = calibration_threshold(calibration)  # fewer than 512 scores stops here
            test_all = list(PREDICTION.iter_unpack((fold_root(k)/'test.bin').read_bytes()))
            rows = method_rows(test_all, loaded['test'], R)
            unsupported = {s: sum(not all(math.isfinite(x) for x in v) for v in loaded[s].values()) for s in SEGMENTS}
            fraction = {s: unsupported[s]/len(loaded[s]) for s in SEGMENTS}
            alarms = episodes_by_event(rows, threshold['threshold'])
            target = frozen/m/f'fold-{k}'; target.mkdir(parents=True)
            write_new(target/'thresholds.json', {**threshold, 'R64': R})
            write_new(target/'episodes.json', {str(e): v for e, v in alarms.items()})
            write_new(target/'test-rows.bin', b''.join(PREDICTION.pack(*r) for r in rows))
            write_new(target/'support.json', {'unsupported': unsupported, 'fraction': fraction,
                                              'stop': any(f > UNSUPPORTED_STOP for f in fraction.values())})
            close(target)
            per[k] = {'threshold': threshold['threshold'], 'calibration_n': threshold['n'], 'unsupported': unsupported,
                      'stop': any(f > UNSUPPORTED_STOP for f in fraction.values()), 'closure_sha256': digest(target/'root-closed.json')}
        close(frozen/m)
        summary['methods'][m] = per
    summary['any_unsupported_stop'] = any(f['stop'] for p in summary['methods'].values() for f in p.values())
    write_new(frozen/'freeze.json', summary); close(frozen)
    print(json.dumps({'freeze_closure_sha256': digest(frozen/'root-closed.json'), 'any_unsupported_stop': summary['any_unsupported_stop']}))


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest='cmd', required=True)
    u = sub.add_parser('unit')
    for a in ('--method', '--segment', '--output', '--cache'):
        u.add_argument(a, required=True)
    u.add_argument('--fold', type=int, required=True); u.add_argument('--chunk', type=int, required=True)
    c = sub.add_parser('campaign'); c.add_argument('--output', required=True); c.add_argument('--venvs', required=True)
    c.add_argument('--parallel', type=int, default=3); c.add_argument('--hours', type=float, default=24)
    f = sub.add_parser('freeze'); f.add_argument('--output', required=True)
    a = p.parse_args()
    if a.cmd == 'unit':
        run_unit(a.method, a.fold, a.segment, a.chunk, a.output, a.cache)
    elif a.cmd == 'campaign':
        assert 1 <= a.parallel <= 3 and a.hours <= 24, 'contract: at most 3 processes and 24 h'
        campaign(a.output, a.venvs, a.parallel, a.hours)
    else:
        freeze(a.output)


if __name__ == '__main__':
    main()
