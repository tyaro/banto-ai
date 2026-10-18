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

    python3 tools/care_fm.py campaign --output artifacts/care-fm-20261017 --venvs <dir with fm-<method>/ and hf-cache/<method>/>
    <dir>/fm-<method>/bin/python tools/care_fm.py environment --method <method> --cache <dir>/hf-cache/<method> \
        --output artifacts/care-fm-20261017      (once per method; freeze requires these records)
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
CALIBRATION_SCORE = struct.Struct('<IId')  # event, origin n, score (NaN if unsupported)
TORCH = '2.14.0+cpu'
ENVIRONMENT = {  # installed distribution and pinned checkpoint of each method (contract + tools/<method>)
    'timesfm3': {'distribution': 'timesfm', 'version': '3.0.0', 'checkpoint': 'google/timesfm-3.0-pytorch',
                 'revision': '43046b85ec22d584a13f8098c2ed39c889e129c2', 'model_bytes': 1_322_898_824,
                 'model_sha256': 'a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da'},
    'chronos2': {'distribution': 'chronos-forecasting', 'version': '2.3.1', 'checkpoint': 'amazon/chronos-2',
                 'revision': '29ec3766d36d6f73f0696f85560a422f50e8498c', 'model_bytes': 477_930_472,
                 'model_sha256': 'ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42'},
    'toto2': {'distribution': 'toto-2', 'version': '2.0.0', 'checkpoint': 'Datadog/Toto-2.0-4m',
              'revision': '8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9', 'model_bytes': 16_582_848,
              'model_sha256': '316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e'}}
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


def verify_closed(root):
    """Every file and sub-root listed in root-closed.json matches, and nothing unlisted exists."""
    root = Path(root); record = json.loads((root/'root-closed.json').read_bytes()); listed = set()
    for f in record['files']:
        name = f['name'].rstrip('/'); listed.add(name)
        if f['name'].endswith('/'):
            verify_closed(root/name)
            if digest(root/name/'root-closed.json') != f['root_closed_sha256']:
                raise ValueError(f'sub-root closure differs: {root/name}')
        elif not (root/name).is_file() or digest(root/name) != f['sha256']:
            raise ValueError(f'closed file differs: {root/name}')
    if {p.name for p in root.iterdir()}-{'root-closed.json'} != listed:
        raise ValueError(f'unlisted files in closed root: {root}')


def check_unit(directory, method, fold, segment, chunk, rows, fold_closure, dataset_closure):
    """A closed chunk is reusable only if its closure verifies, it is the expected unit on the
    expected inputs, and its recorded time and memory are within the contract's limits."""
    verify_closed(directory)
    info = json.loads((Path(directory)/'unit.json').read_bytes())
    if (info['method'], info['fold'], info['segment'], info['chunk'], info['rows']) != (method, fold, segment, chunk, rows):
        raise ValueError(f'unit identity differs: {directory}')
    if info['fold_root_closure_sha256'] != fold_closure or info['dataset_closure_sha256'] != dataset_closure:
        raise ValueError(f'unit inputs differ from the closed roots: {directory}')
    if info['seconds'] > 870 or info['peak_rss_bytes'] > MEMORY[method]:
        raise ValueError(f'unit over the time or memory limit: {directory}')
    if len((Path(directory)/'predictions.bin').read_bytes()) != rows*PRED.size:
        raise ValueError(f'prediction size differs: {directory}')
    return info


def verify_record(out, method):
    """The pinned fields of the closed environment record, for comparison with a unit's."""
    record = json.loads((Path(out)/'environment'/method/'environment.json').read_bytes())
    return {k: record[k] for k in ('method', 'distribution', 'version', 'torch', 'checkpoint', 'revision', 'model_bytes', 'model_sha256')}


def expected_unit(method, fold, segment, chunk):
    return dict(method=method, fold=fold, segment=segment, chunk=chunk, rows=len(chunks(fold, segment)[chunk]),
                fold_closure=digest(fold_root(fold)/'root-closed.json'), dataset_closure=digest(DATASET/'root-closed.json'))


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


def verify_environment(method, cache):
    """The installed package and Torch versions and the cached checkpoint (revision, size,
    SHA-256 of model.safetensors) must be the pinned ones; returns what was verified."""
    import importlib.metadata
    pin = ENVIRONMENT[method]
    installed = importlib.metadata.version(pin['distribution']); torch = importlib.metadata.version('torch')
    if installed != pin['version'] or torch != TORCH:
        raise RuntimeError(f'{method}: installed {pin["distribution"]} {installed} / torch {torch} differ from the pins')
    models = [m for m in Path(cache).rglob('model.safetensors') if m.parent.name == pin['revision']]
    if len(models) != 1:
        raise RuntimeError(f'{method}: expected one cached snapshot at revision {pin["revision"]}, found {len(models)}')
    model = models[0].resolve(); size = model.stat().st_size; sha = digest(model)
    if size != pin['model_bytes'] or sha != pin['model_sha256']:
        raise RuntimeError(f'{method}: model.safetensors {size} B / {sha} differ from the pins')
    return {'method': method, 'distribution': pin['distribution'], 'version': installed, 'torch': torch,
            'checkpoint': pin['checkpoint'], 'revision': pin['revision'], 'model_bytes': size, 'model_sha256': sha}


def write_environment(method, cache, out):
    """A closed record of the verified environment, with the latest modification time of the
    installed packages and the cached snapshot (evidence of whether they changed during a run)."""
    import site
    record = verify_environment(method, cache)
    packages = [Path(p) for p in site.getsitepackages()]
    newest = lambda roots: max((f.stat().st_mtime for r in roots for f in r.rglob('*') if f.is_file()), default=0)
    record['site_packages_latest_mtime_utc'] = datetime.fromtimestamp(newest(packages), timezone.utc).isoformat()
    record['checkpoint_cache_latest_mtime_utc'] = datetime.fromtimestamp(newest([Path(cache)]), timezone.utc).isoformat()
    record['verified_at_utc'] = datetime.now(timezone.utc).isoformat()
    target = Path(out)/'environment'/method; target.mkdir(parents=True)
    write_new(target/'environment.json', record); close(target)
    print(json.dumps(record))


def run_unit(method, fold, segment, chunk, out, cache):
    import resource
    import torch
    from care_input import Consumer, pinned_input
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    started = time.monotonic(); target = unit_dir(out, method, fold, segment, chunk); target.mkdir(parents=True)
    rows = chunks(fold, segment)[chunk]
    environment = verify_environment(method, cache)  # a mismatch stops the unit before any inference
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
        'dataset_closure_sha256': digest(DATASET/'root-closed.json'), 'torch': torch.__version__, 'environment': environment,
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
            try:  # a closed chunk is reused only if it still verifies and stayed within the limits
                check_unit(d, **expected_unit(*unit))
            except ValueError as error:
                stop(log, {}, {'event': 'stop', 'reason': 'closed chunk fails verification', 'unit': unit, 'error': str(error)})
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
    out = Path(out)
    for k in FOLDS:
        verify_closed(fold_root(k))
    verify_closed(DATASET)
    environments = {}
    for m in METHODS:  # every method needs a verified environment record (written by `environment`)
        verify_closed(out/'environment'/m)
        record = json.loads((out/'environment'/m/'environment.json').read_bytes())
        if any(record[k] != v for k, v in ENVIRONMENT[m].items() if k in record and k not in ('distribution',)) or record['torch'] != TORCH:
            raise ValueError(f'environment record of {m} differs from the pins')
        environments[m] = digest(out/'environment'/m/'root-closed.json')
    frozen = out/'frozen'; frozen.mkdir()
    summary = {'methods': {}, 'labels_read': False, 'environment_closure_sha256': environments}
    for m in METHODS:
        per = {}
        for k in FOLDS:
            R = [v['R64'] for v in json.loads((fold_root(k)/'input.json').read_bytes())['profile']['alarm_scales']]
            loaded = {}; chunk_closures = {}
            for s in SEGMENTS:
                dirs = [unit_dir(out, m, k, s, c) for c in range(len(chunks(k, s)))]
                for c, d in enumerate(dirs):
                    info = check_unit(d, **expected_unit(m, k, s, c))
                    if 'environment' in info and info['environment'] != verify_record(out, m):
                        raise ValueError(f'unit environment differs from the environment record: {d}')
                chunk_closures[s] = [digest(d/'root-closed.json') for d in dirs]
                loaded[s] = assemble(saved_rows(k, s), [(d/'predictions.bin').read_bytes() for d in dirs])
            calibration_rows = [(r[0], r[1], score(r, loaded['calibration'][(r[0], r[1])], R)
                                 if all(math.isfinite(x) for x in loaded['calibration'][(r[0], r[1])]) else math.nan)
                                for r in saved_rows(k, 'calibration')]
            calibration = [x for _, _, x in calibration_rows if math.isfinite(x)]
            threshold = calibration_threshold(calibration)  # fewer than 512 scores stops here
            test_all = list(PREDICTION.iter_unpack((fold_root(k)/'test.bin').read_bytes()))
            rows = method_rows(test_all, loaded['test'], R)
            unsupported = {s: sum(not all(math.isfinite(x) for x in v) for v in loaded[s].values()) for s in SEGMENTS}
            fraction = {s: unsupported[s]/len(loaded[s]) for s in SEGMENTS}
            alarms = episodes_by_event(rows, threshold['threshold'])
            target = frozen/m/f'fold-{k}'; target.mkdir(parents=True)
            write_new(target/'thresholds.json', {**threshold, 'R64': R})
            write_new(target/'calibration-scores.bin', b''.join(CALIBRATION_SCORE.pack(*r) for r in calibration_rows))
            write_new(target/'chunks.json', {'chunk_root_closed_sha256': chunk_closures,
                                             'fold_root_closure_sha256': digest(fold_root(k)/'root-closed.json')})
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
    e = sub.add_parser('environment'); e.add_argument('--method', required=True); e.add_argument('--cache', required=True)
    e.add_argument('--output', required=True)
    a = p.parse_args()
    if a.cmd == 'unit':
        run_unit(a.method, a.fold, a.segment, a.chunk, a.output, a.cache)
    elif a.cmd == 'environment':
        write_environment(a.method, a.cache, a.output)
    elif a.cmd == 'campaign':
        assert 1 <= a.parallel <= 3 and a.hours <= 24, 'contract: at most 3 processes and 24 h'
        campaign(a.output, a.venvs, a.parallel, a.hours)
    else:
        freeze(a.output)


if __name__ == '__main__':
    main()
