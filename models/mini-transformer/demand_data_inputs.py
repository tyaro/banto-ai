"""New input adapter; retains the saved original splits/scales/batch schedule."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import torch
from demand_data import STORES, load_snapshot as load_original_snapshot
from demand_input_features import build_inputs, training_support
from verification_records import verify_record


class PreparedInputs:
    def __init__(self, original, declaration, support, support_pin):
        self.histories = original.histories
        self.train_scale = original.train_scale
        self.origins, self.excluded = original.origins, original.excluded
        if declaration['stores'] != list(STORES) or declaration['train_scale'] != self.train_scale.tolist():
            raise ValueError('saved train scale/order mismatch')
        if declaration['origins'] != {s: [str(d) for d in ds] for s, ds in self.origins.items()}:
            raise ValueError('saved split/origin mismatch')
        self.fixed_schedule = [[dt.date.fromisoformat(d) for d in row] for row in declaration['schedule']]
        if len(self.fixed_schedule) != 256 or any(len(row) != 8 or any(d not in self.origins['train'] for d in row) for row in self.fixed_schedule):
            raise ValueError('saved schedule mismatch')
        self.scales = dict(zip(STORES, self.train_scale.tolist()))
        self.support = support
        self.support_pin = support_pin

    def built(self, origin):
        value = build_inputs(self.histories, origin, self.scales, self.support)
        if not value['available']:
            raise ValueError('unavailable input: '+str({s: row['reason'] for s, row in value['stores'].items()}))
        return value

    def features(self, origin):
        value = self.built(origin); rows = [value['stores'][s] for s in STORES]
        return (torch.tensor([r['values'] for r in rows], dtype=torch.float32),
                torch.tensor([r['observed'] for r in rows], dtype=torch.bool),
                torch.tensor(value['past_calendar'], dtype=torch.float32),
                torch.tensor(value['future_calendar'], dtype=torch.float32),
                torch.tensor([r['baseline'] for r in rows], dtype=torch.float32),
                torch.tensor([r['context_statistics'] for r in rows], dtype=torch.float32))

    def batch(self, dates, split):
        if not 1 <= len(dates) <= 8 or any(d not in self.origins[split] for d in dates):
            raise ValueError('origin excluded or in wrong split')
        rows = [self.features(d) for d in dates]
        x = tuple(torch.stack([r[k] for r in rows]) for k in range(6))
        labels = torch.tensor([[[self.histories[s][d+dt.timedelta(days=k)] for k in range(14)]
                               for s in STORES] for d in dates], dtype=torch.float32)
        return x, labels

    def schedule(self):
        return [list(row) for row in self.fixed_schedule]

    def description(self):
        return {'stores': STORES, 'family': 'BREAD/BAKERY', 'context': 56, 'horizon': 14,
                'origins': {s: [str(d) for d in ds] for s, ds in self.origins.items()},
                'excluded': self.excluded, 'train_scale': self.train_scale.tolist(),
                'schedule': [[str(d) for d in row] for row in self.fixed_schedule],
                'training_event_support': self.support, 'support_binding': self.support_pin,
                'calendar_features': 12, 'context_statistics': 2,
                'test_status': 'already inspected 2017; exploratory candidate prompted by earlier results'}


def load_snapshot(repo):
    original, binding = load_original_snapshot(repo)
    modelroot = Path(repo)/'artifacts/representative-store-sales-small-model-pilot-20261014'
    closed = json.loads((modelroot/'root-closed.json').read_bytes())
    raw = (modelroot/'input.json').read_bytes()
    pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if closed['status'] != 'complete' or pin != closed['files']['input.json']:
        raise ValueError('original input pin mismatch')
    declaration = json.loads(raw)
    if declaration['binding'] != binding:
        raise ValueError('same input snapshot required')
    root = Path(repo)/'artifacts/representative-store-sales-training-diagnosis-20261014-records'
    manifest = verify_record(root)
    if manifest['status'] != 'complete':
        raise ValueError('training support incomplete')
    raw_support = b''.join((root/p['path']).read_bytes() for p in manifest['items']['event-support-ledger']['parts'])
    support = training_support(json.loads(raw_support), dt.date(2016, 1, 1))
    support_pin = {'bytes': len(raw_support), 'sha256': hashlib.sha256(raw_support).hexdigest(), 'record': str(root)}
    return PreparedInputs(original, declaration, support, support_pin), dict(binding, original_input=pin)
