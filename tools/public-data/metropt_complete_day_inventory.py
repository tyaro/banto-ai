"""One timestamp-only complete-day calendar revision. Never parses sensor values."""
from array import array
from datetime import datetime, timedelta
import json
from pathlib import Path
import traceback
import zipfile
from macos_industrial_fetch import ROOT, close, digest, write
from macos_demand_runtime import MacCheckpoint


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--archive', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    archive, out = Path(a.archive), Path(a.output)
    out.mkdir(parents=True, exist_ok=False)
    check = MacCheckpoint(seconds=870)
    status = 'failed'
    try:
        expected = json.loads((ROOT/'datasets/manifests/metropt3-source.json').read_text())['archive']
        if archive.stat().st_size != expected['size_bytes'] or digest(archive) != expected['sha256']:
            raise ValueError('archive pin mismatch')
        write(out/'prescan-contract.json', {
            'selection': 'first 13 complete days chronologically, excluding observed 2020-02-21',
            'complete': 'all 1440 minute bins occupied and max within-day consecutive raw gap <=60s',
            'splits': [7, 3, 3], 'cross_day_windows': False,
            'quantity_decode_allowed': False, 'shortfall': 'stop, no replacement rule',
            'source_sha256': digest(__file__),
            'prior_calendar_closure_sha256': digest(ROOT/'artifacts/metropt-multiday-timestamp-20261016/root-closed.json')})
        (out/'source.py').write_bytes(Path(__file__).read_bytes())
        days = {}
        rows = duplicates = reversals = 0
        first = last = previous = None
        with zipfile.ZipFile(archive) as z, z.open('MetroPT3(AirCompressor).csv') as f:
            if f.readline().rstrip(b'\r\n').split(b',')[1] != b'timestamp':
                raise ValueError('timestamp header mismatch')
            for line in f:
                _, sep, rest = line.partition(b',')
                raw, sep2, _ = rest.partition(b',')
                if not sep or not sep2: raise ValueError('timestamp delimiter missing')
                t = datetime.fromisoformat(raw.decode('ascii'))
                if t.tzinfo is not None: raise ValueError('unexpected timezone')
                key = t.date().isoformat()
                d = days.setdefault(key, {'counts': array('I', [0])*1440, 'max_gap': 0})
                d['counts'][t.hour*60+t.minute] += 1
                if previous is not None:
                    gap = (t-previous).total_seconds()
                    duplicates += gap == 0
                    reversals += gap < 0
                    if previous.date() == t.date(): d['max_gap'] = max(d['max_gap'], gap)
                if first is None: first = t
                last = previous = t
                rows += 1
                if rows % 10000 == 0: check.check()
        inventory = []
        day = first.date()
        while day <= last.date():
            key = day.isoformat()
            d = days.get(key, {'counts': [0]*1440, 'max_gap': 0})
            empty = sum(n == 0 for n in d['counts'])
            reasons = []
            if empty: reasons.append('empty_minute_bins')
            if d['max_gap'] > 60: reasons.append('within_day_raw_gap_over_60s')
            if key == '2020-02-21': reasons.append('previously_observed_day')
            inventory.append({'date': key, 'rows': sum(d['counts']), 'empty_minutes': empty,
                              'max_within_day_gap_seconds': d['max_gap'],
                              'eligible': not reasons, 'exclusion_reasons': reasons})
            day += timedelta(days=1)
        if duplicates or reversals: raise ValueError('global duplicate/reversed timestamp')
        eligible = [d['date'] for d in inventory if d['eligible']]
        write(out/'all-day-inventory.json', inventory)
        if len(eligible) < 13: raise ValueError('fewer than 13 complete days')
        selected = { 'train': eligible[:7], 'validation': eligible[7:10], 'test': eligible[10:13] }
        windows = []
        for split, dates in selected.items():
            for key in dates:
                for n in range(128, 1409, 1 if split == 'train' else 32):
                    windows.append({'split': split, 'day': key, 'origin_minute_in_day': n,
                                    'issue_time_source_naive': (datetime.fromisoformat(key)+timedelta(minutes=n)).isoformat(),
                                    'context_bins': [n-128, n], 'target_bins': [n, n+32],
                                    'timestamp_eligible': True})
        with (out/'calendar-windows.jsonl').open('x') as f:
            for w in windows: f.write(json.dumps(w, separators=(',', ':'))+'\n')
        write(out/'selected-minute-coverage.json', {key: list(days[key]['counts']) for dates in selected.values() for key in dates})
        summary = {'status': 'timestamp-calendar-fixed', 'archive_sha256': expected['sha256'],
                   'source_rows': rows, 'source_first': first.isoformat(), 'source_last': last.isoformat(),
                   'duplicates': duplicates, 'reversals': reversals, 'eligible_day_count': len(eligible),
                   'selected_days': selected,
                   'candidate_windows': {s: sum(w['split'] == s for w in windows) for s in selected},
                   'minimum_common_support_per_day': {'train': 1153, 'validation': 37, 'test': 37},
                   'quantity_values_decoded': 0, 'quantity_validity': 'not checked', 'model_runs': 0,
                   'can_launch_learning': False, 'resources': check.check()}
        write(out/'summary.json', summary)
        status = 'complete'
        print(json.dumps(summary))
    except BaseException:
        write(out/'failure.json', {'traceback': traceback.format_exc()})
        raise
    finally:
        close(out, status)


if __name__ == '__main__': main()
