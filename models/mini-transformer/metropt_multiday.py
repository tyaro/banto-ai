"""Fixed r2 MetroPT contract and binary adapter. No model or training on import.

Portable storage: little-endian float32 [day,target,minute]; targets in config order.
Test readers expose issued contexts only; test targets belong to the gated scorer.
"""
from array import array
from datetime import datetime, timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import random
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT/'examples/configs/metropt-macos-multiday-20261016.json'
CONFIG_SHA = 'd0227b12b5d8a00fb7b5bec4792dbccb3cc802e486bdb28e9ffb960fc605d2ed'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()


def contract():
    c = json.loads(CONFIG.read_bytes())
    if digest(CONFIG) != CONFIG_SHA: raise ValueError('fixed contract changed')
    for path, expected in [(c['source']['calendar_manifest'], c['source']['calendar_sha256']),
                           ('models/mini-transformer/small_model.py', c['source']['model_source_sha256']),
                           ('artifacts/metropt-complete-days-timestamp-20261016/root-closed.json', c['source']['timestamp_closure_sha256'])]:
        if digest(ROOT/path) != expected: raise ValueError('source/calendar pin mismatch: '+path)
    return c


def f32(x):
    y = struct.unpack('<f', struct.pack('<f', x))[0]
    if not math.isfinite(y): raise ValueError('float32 nonfinite')
    return y


def scales(train_days):
    result = []
    for v in range(3):
        xs = [float(x) for day in train_days for x in day[v]]
        if not xs or not all(math.isfinite(x) for x in xs): raise ValueError('invalid scale population')
        mean = math.fsum(xs)/len(xs)
        var = math.fsum((x-mean)**2 for x in xs)/len(xs)
        sigma = math.sqrt(var)
        t, floor = max(sigma, 1e-5), max(.01*sigma, 1e-5)
        if not all(math.isfinite(x) for x in (mean, var, sigma, t, floor)): raise ValueError('nonfinite scale')
        t32, floor32 = f32(t), f32(floor)
        if min(t, floor, t32, floor32) <= 0: raise ValueError('nonpositive scale')
        result.append({'n': len(xs), 'mean64': mean, 'variance64': var, 'sigma64': sigma,
                       'T64': t, 'floor64': floor, 'T32': t32, 'floor32': floor32})
    return result


def origins(split):
    if split not in ('train','validation','test'): raise ValueError('unknown split')
    return list(range(128, 1409, 1 if split == 'train' else 32))


def common_origins(values, valid, split):
    if len(values) != 3 or len(valid) != 3 or any(len(row) != 1440 for row in [*values,*valid]):
        raise ValueError('day shape')
    invalid = [0]
    for n in range(1440):
        invalid.append(invalid[-1]+int(any(not valid[v][n] or not math.isfinite(values[v][n]) for v in range(3))))
    keep, excluded = [], []
    for n in origins(split):
        if invalid[n+32] != invalid[n-128]: excluded.append(n)
        else: keep.append(n)
    minimum = (9*len(origins(split))+9)//10
    if len(keep) < minimum: raise ValueError('daily common support below fixed threshold')
    return keep, excluded


def encode_f32(values):
    a = array('f', values)
    if a.itemsize != 4: raise ValueError('unexpected float width')
    if sys.byteorder != 'little': a.byteswap()
    return a.tobytes()


class Files:
    """Exclusive flat writer. Budget includes closure and preserves failure reserve."""
    def __init__(self, root):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=False)
        self.closed = False

    def write(self, name, raw, failure=False):
        if self.closed or Path(name).name != name or (self.root/name).exists(): raise ValueError('closed/reused/unsafe output')
        files = list(self.root.iterdir())
        if any(not p.is_file() or p.is_symlink() for p in files): raise ValueError('invalid output entry')
        count, size = (32, 1024**3) if failure else (23, 768*1024**2)
        if len(files)+1 > count or len(raw) > 32*1024**2 or sum(p.stat().st_size for p in files)+len(raw) > size:
            raise RuntimeError('artifact budget exceeded')
        with (self.root/name).open('xb') as f:
            if f.write(raw) != len(raw): raise OSError('short write')

    def json(self, name, value, failure=False):
        self.write(name, (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode(), failure)

    def close(self, status):
        files = [{'name':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(self.root.iterdir())]
        self.json('root-closed.json', {'status':status,'files':files}, True); self.closed = True

    def sources(self, paths):
        b = io.BytesIO()
        with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
            for p in paths: z.write(p, Path(p).relative_to(ROOT).as_posix())
        self.write('sources.zip', b.getvalue())


def verify_closed(root):
    root = Path(root)
    c = json.loads((root/'root-closed.json').read_bytes())
    if c['status'] != 'complete': raise ValueError('input root incomplete')
    for item in c['files']:
        name = item['name']
        if Path(name).name != name or (root/name).is_symlink(): raise ValueError('invalid input path')
        if (root/name).stat().st_size != item['bytes'] or digest(root/name) != item['sha256']:
            raise ValueError('input digest mismatch: '+name)
    if set(p.name for p in root.iterdir()) != {x['name'] for x in c['files']}|{'root-closed.json'}:
        raise ValueError('unlisted input files')
    return c


class Reader:
    def __init__(self, directory, split):
        self.root, self.split = Path(directory), split
        self.config = contract()
        verify_closed(self.root)
        self.manifest = json.loads((self.root/'dataset.json').read_bytes())
        if self.manifest['config_sha256'] != CONFIG_SHA: raise ValueError('prepared config differs')
        self.days = self.config['calendar']['selected_days'][split]
        if self.manifest['days'] != self.config['calendar']['selected_days']: raise ValueError('prepared day mapping differs')
        self.support = json.loads((self.root/'support.json').read_bytes())[split]
        self.keys = [(day,n) for day in self.days for n in self.support[day]['kept']]
        self.allowed = set(self.keys)
        self.file = self.root/(split+'.f32')
        if self.file.stat().st_size != len(self.days)*3*1440*4: raise ValueError('binary size/layout')
        self.stats = json.loads((self.root/'scales.json').read_bytes())

    def _slice(self, key, left, right):
        day, n = tuple(key)
        if (day,n) not in self.allowed or not 0 <= left < right <= 1440: raise ValueError('invalid split/day/origin slice')
        d = self.days.index(day); rows = []
        with self.file.open('rb') as f:
            for v in range(3):
                f.seek(((d*3+v)*1440+left)*4)
                raw = f.read((right-left)*4)
                row = struct.unpack('<'+'f'*(right-left),raw)
                if not all(math.isfinite(x) for x in row): raise ValueError('invalid materialized quantity')
                rows.append(row)
        return rows

    def context(self, key): return self._slice(key, key[1]-128, key[1])

    def targets(self, key):
        if self.split == 'test': raise PermissionError('test targets belong to freeze-gated scorer')
        return self._slice(key,key[1],key[1]+32)

    def batch(self, keys, labels=True):
        import torch
        if not 1 <= len(keys) <= 8: raise ValueError('batch size')
        x = torch.tensor([self.context(key) for key in keys],dtype=torch.float32)
        if not labels: return x
        y = torch.tensor([self.targets(key) for key in keys],dtype=torch.float32)
        return x,y

    def schedule(self, seed):
        if self.split != 'train': raise PermissionError('sampler requires train')
        rng = random.Random(seed); by_day = {d:[key for key in self.keys if key[0]==d] for d in self.days}
        schedule = []
        for _ in range(4096):
            batch=[]
            for _ in range(8):
                day = self.days[rng.randrange(7)]; entries = by_day[day]
                batch.append(entries[rng.randrange(len(entries))])
            schedule.append(batch)
        return schedule


def issue(key): return (datetime.fromisoformat(key[0])+timedelta(minutes=key[1])).isoformat()


def baseline(context, mode):
    if mode not in ('last-value','moving-average-15'): raise ValueError('baseline mode')
    return [[f32(row[-1] if mode == 'last-value' else math.fsum(row[-15:])/15)]*32 for row in context]


def mean(xs):
    xs=list(xs)
    if not xs: raise ValueError('empty metric support')
    result=math.fsum(xs)/len(xs)
    if not math.isfinite(result): raise ValueError('nonfinite metric')
    return result


def pinball_score(predictions, actuals, keys, train_scale):
    daily={}
    for pred,y,key in zip(predictions,actuals,keys,strict=True):
        target_scores=[]
        for v in range(3):
            leads=[]
            for h in range(32):
                losses=[]
                for j,tau in enumerate((.1,.5,.9)):
                    e=(float(y[v][h])-float(pred[v][h][j]))/train_scale[v]
                    losses.append(max(tau*e,(tau-1)*e))
                leads.append(mean(losses))
            target_scores.append(mean(leads))
        daily.setdefault(key[0],[]).append(target_scores)
    return mean(mean(mean(row[v] for row in rows) for v in range(3)) for rows in daily.values())


def baseline_selection(reader):
    results={mode:[{} for _ in range(3)] for mode in ('last-value','moving-average-15')}
    for key in reader.keys:
        x,y=reader.context(key),reader.targets(key)
        for mode in results:
            p=baseline(x,mode)
            for v in range(3): results[mode][v].setdefault(key[0],[]).append(mean(abs(y[v][h]-p[v][h]) for h in range(32)))
    scores={mode:[mean(mean(xs) for xs in days.values()) for days in targets] for mode,targets in results.items()}
    selected=[min(scores,key=lambda mode:(scores[mode][v],mode!='last-value')) for v in range(3)]
    return {'selected_per_target':selected,'validation_mae':scores}
