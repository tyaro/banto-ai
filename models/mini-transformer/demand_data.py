"""Public saved demand snapshot; origin-past features and split-local labels."""
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import random

import torch

STORES = (5, 11, 12)
START = dt.date(2013, 1, 1)
EVENTS = {(1, 1), (5, 1), (5, 24), (8, 10), (10, 9), (11, 2), (11, 3), (12, 25)}


def calendar(day):
    length = (dt.date(day.year+1, 1, 1)-dt.date(day.year, 1, 1)).days
    annual = 2*math.pi*(day-dt.date(day.year, 1, 1)).days/length
    weekly = 2*math.pi*day.weekday()/7
    return [math.sin(weekly), math.cos(weekly), math.sin(annual), math.cos(annual),
            float((day.month, day.day) in EVENTS)]


def origins(split):
    if split == 'train':
        first, last = START+dt.timedelta(days=56), dt.date(2015, 12, 18)
        return [first+dt.timedelta(days=k) for k in range((last-first).days+1)]
    if split in ('validation', 'test'):
        first, n = (dt.date(2016, 1, 1), 26) if split == 'validation' else (dt.date(2017, 1, 1), 16)
        return [first+dt.timedelta(days=14*k) for k in range(n)]
    raise ValueError('unknown split')


class Prepared:
    def __init__(self, histories):
        if set(histories) != set(STORES):
            raise ValueError('unexpected store mapping')
        self.histories = histories
        self.train_scale = torch.tensor([max(1., sum(values)/len(values)) for values in
            [[v for d, v in histories[s].items() if d < dt.date(2016, 1, 1) and v is not None]
             for s in STORES]], dtype=torch.float32)
        self.origins, self.excluded = {}, {}
        for split in ('train', 'validation', 'test'):
            self.origins[split], self.excluded[split] = [], []
            for origin in origins(split):
                reason = None
                for s in STORES:
                    if any(histories[s].get(origin+dt.timedelta(days=k)) is None for k in range(14)):
                        reason = 'missing_target'
                        break
                    if any(not any(histories[s].get(origin-dt.timedelta(days=k)) is not None
                                   for k in range(1, 29) if (origin-dt.timedelta(days=k)).weekday() == w)
                           for w in range(7)):
                        reason = 'no_observed_weekday_in_past28'
                        break
                if reason:
                    self.excluded[split].append({'origin': str(origin), 'reason': reason})
                else:
                    self.origins[split].append(origin)
        if any(not v for v in self.origins.values()):
            raise ValueError('empty required split')

    def features(self, origin):
        # Never inspect any origin-or-later quantity while constructing features.
        days = [origin-dt.timedelta(days=k) for k in range(56, 0, -1)]
        future = [origin+dt.timedelta(days=k) for k in range(14)]
        values, masks, bases = [], [], []
        for s in STORES:
            past = [self.histories[s].get(d) for d in days]
            values.append([0. if v is None else v for v in past])
            masks.append([v is not None for v in past])
            b = []
            for day in future:
                support = [v for d, v in zip(days[-28:], past[-28:])
                           if d.weekday() == day.weekday() and v is not None]
                if not support:
                    raise ValueError('no weekday support')
                b.append(math.fsum(support)/len(support))
            bases.append(b)
        return (torch.tensor(values, dtype=torch.float32), torch.tensor(masks, dtype=torch.bool),
                torch.tensor([calendar(d) for d in days], dtype=torch.float32),
                torch.tensor([calendar(d) for d in future], dtype=torch.float32),
                torch.tensor(bases, dtype=torch.float32))

    def batch(self, dates, split):
        if not 1 <= len(dates) <= 8 or any(d not in self.origins[split] for d in dates):
            raise ValueError('origin excluded or in wrong split')
        features = [self.features(d) for d in dates]
        x = tuple(torch.stack([r[k] for r in features]) for k in range(5))
        labels = torch.tensor([[[self.histories[s][d+dt.timedelta(days=k)] for k in range(14)]
                               for s in STORES] for d in dates], dtype=torch.float32)
        return x, labels

    def schedule(self):
        rng = random.Random(20261015)
        return [[rng.choice(self.origins['train']) for _ in range(8)] for _ in range(256)]

    def description(self):
        return {'stores': STORES, 'family': 'BREAD/BAKERY', 'context': 56, 'horizon': 14,
                'origins': {s: [str(d) for d in ds] for s, ds in self.origins.items()},
                'excluded': self.excluded, 'train_scale': self.train_scale.tolist(),
                'schedule': [[str(d) for d in row] for row in self.schedule()],
                'test_status': 'already inspected public 2017; retrospective exploration'}


def load_snapshot(repo):
    from verification_records import verify_record
    root = Path(repo)/'artifacts/representative-store-sales-cross-city-20261014-records'
    manifest = verify_record(root)
    if manifest['status'] != 'complete':
        raise ValueError('snapshot record incomplete')
    raw = b''.join((root/p['path']).read_bytes() for p in manifest['items']['selected-input-csv']['parts'])
    histories = {s: {} for s in STORES}
    for row in csv.DictReader(io.StringIO(raw.decode('utf-8'))):
        s, day = int(row['store_nbr']), dt.date.fromisoformat(row['date'])
        if s not in histories or day in histories[s] or row['observed'] not in ('0', '1'):
            raise ValueError('invalid snapshot identity')
        if (row['observed'] == '1') != (row['sales'] != ''):
            raise ValueError('missing/quantity mismatch')
        v = float(row['sales']) if row['sales'] else None
        if v is not None and (not math.isfinite(v) or v < 0):
            raise ValueError('invalid observed quantity')
        histories[s][day] = v
    expected = {START+dt.timedelta(days=k) for k in range(1687)}
    if any(set(h) != expected for h in histories.values()):
        raise ValueError('snapshot date coverage mismatch')
    data = Prepared(histories)
    if data.origins['test'] != origins('test'):
        raise ValueError('fixed test windows unexpectedly excluded')
    return data, {'record': str(root), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
