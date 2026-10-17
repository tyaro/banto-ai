"""Run the frozen three-store, three-origin 2017 final exploratory pair once.

Use a fresh evidence root; a failed or completed run cannot be reopened. The
competition test, promotion, oil and transactions stay unused.
"""
from pathlib import Path
import argparse
import csv
import ctypes
import datetime as dt
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import time
import zipfile

from demand_forecasting import finite_quantity, forecast_pair, metrics
from verification_records import EvidenceStore, verify_record

REPO = Path(__file__).resolve().parents[1]
ORIGINS = [dt.date(2017, month, 1) for month in (2, 5, 8)]
START, PREFIX_END, END = dt.date(2013, 1, 1), dt.date(2015, 12, 31), dt.date(2017, 8, 14)
SOURCES = ['tools/demand_forecasting.py', 'tools/store_sales_final.py', 'tests/test_demand_forecasting.py']


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def private_memory():
    """Current-process private bytes and OS peak pagefile bytes, on Windows."""
    if os.name != 'nt':
        raise RuntimeError('this local execution requires the Windows memory checkpoint')
    from ctypes import wintypes as w
    class Memory(ctypes.Structure):
        _fields_ = [('cb', w.DWORD), ('faults', w.DWORD)] + [(name, ctypes.c_size_t) for name in
            ('peak_working', 'working', 'peak_paged', 'paged', 'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile', 'private')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.POINTER(Memory), w.DWORD]
    psapi.GetProcessMemoryInfo.restype = w.BOOL
    value = Memory()
    value.cb = ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return max(value.private, value.peak_pagefile)


def run(record_root):
    root = Path(record_root).absolute()
    if root.parent != REPO / 'artifacts' or root.exists():
        raise ValueError('a fresh root immediately under artifacts is required')
    started, peak = time.monotonic(), 0
    def checkpoint():
        nonlocal peak
        peak = max(peak, private_memory())
        if time.monotonic() - started > 900 or peak > 2*1024**3:
            raise RuntimeError('execution resource limit; preserve evidence and stop')
        files = list(root.iterdir())
        if len(files) > 32 or any(p.stat().st_size > 32*1024**2 for p in files) or sum(p.stat().st_size for p in files) > 1024**3:
            raise RuntimeError('execution output/file limit')

    with EvidenceStore(root) as evidence:
        with evidence.operation('final-pair', {'origins': [str(date) for date in ORIGINS], 'stores': [1, 2, 3], 'horizon': 14}):
            source_raws = {name: (REPO / name).read_bytes() for name in SOURCES}
            for index, (name, raw) in enumerate(source_raws.items()):
                evidence.write_bytes('calculator-source-' + str(index), raw)
            with evidence.operation('git-base-revision', {'read_only': True}) as operation:
                revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True, timeout=10)
                operation.capture_process(revision)
            evidence.write_json('provenance', {'base_head': revision.stdout.decode().strip(),
                'working_sources': {name: pin(raw) for name, raw in source_raws.items()},
                'working_sources_not_yet_committed': True, 'python': platform.python_version(),
                'machine': platform.machine(), 'execution_limits': {'wall_seconds': 900, 'private_bytes': 2*1024**3,
                'output_bytes': 1024**3, 'single_bytes': 32*1024**2, 'files': 32},
                'native_capacity_proof': False, 'formal_permission': False})
            validation_root = REPO / 'artifacts/representative-store-sales-validation-20261014-records'
            validation_saved = verify_record(validation_root)
            if validation_saved['status'] != 'complete':
                raise ValueError('validation evidence is incomplete')
            validation_summary = json.loads(b''.join((validation_root / part['path']).read_bytes()
                for part in validation_saved['items']['summary']['parts']))
            frozen_core = validation_summary['calculator_pins']['tools/demand_forecasting.py']
            if pin(source_raws['tools/demand_forecasting.py']) != frozen_core:
                raise ValueError('forecaster changed after validation; final execution refused')
            evidence.write_json('frozen-core-binding', {'validation_core': frozen_core,
                'model_parameters_changed': False, 'validation_recomputed': False})
            prior_root = REPO / 'artifacts/representative-store-sales-contract-continuation-20261014-records'
            prior = verify_record(prior_root)
            if prior['status'] != 'complete':
                raise ValueError('input contract record incomplete')
            def prior_bytes(label):
                return b''.join((prior_root / part['path']).read_bytes() for part in prior['items'][label]['parts'])
            contract_raw = prior_bytes('input-contract')
            contract = json.loads(contract_raw)
            if contract['family'] != 'BREAD/BAKERY' or contract['stores'] != [1, 2, 3] or contract['final_origins'] != [str(d) for d in ORIGINS]:
                raise ValueError('frozen contract mismatch')
            evidence.write_json('contract-binding', {'record_root': str(prior_root), 'contract': pin(contract_raw), 'recipe': contract})
            histories = {store: {} for store in (1, 2, 3)}
            prefix_raw = prior_bytes('training-calendar-csv')
            for row in csv.DictReader(io.StringIO(prefix_raw.decode('utf-8'))):
                date, store = dt.date.fromisoformat(row['date']), int(row['store_nbr'])
                if row['family'] != 'BREAD/BAKERY' or date < START or date > PREFIX_END or date in histories[store]:
                    raise ValueError('prior prefix key mismatch')
                observed = row['observed'] == '1'
                if observed != (row['sales'] != ''):
                    raise ValueError('prior prefix missing mask mismatch')
                histories[store][date] = finite_quantity(float(row['sales'])) if observed else None
            source_root = REPO / 'data/public/store-sales-user-provided-20261014'
            manifest = json.loads((source_root / 'source-manifest.json').read_bytes())
            archive_path = source_root / manifest['archive']['filename']
            stat = archive_path.lstat()
            if archive_path.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 1024:
                raise ValueError('reparse input refused')
            before = (stat.st_size, stat.st_mtime_ns, stat.st_dev, stat.st_ino)
            digest = hashlib.sha256()
            with archive_path.open('rb') as stream:
                while raw := stream.read(1024**2):
                    checkpoint()
                    digest.update(raw)
            if stat.st_size != manifest['archive']['bytes'] or digest.hexdigest() != contract['source_archive_sha256']:
                raise ValueError('source archive pin mismatch')
            evidence.write_json('input-binding', {'archive': manifest['archive'], 'prefix_csv': pin(prefix_raw),
                'source_identity': before, '2017_numeric_values_parsed': True, 'unparsed_predictors': ['onpromotion', 'oil', 'transactions']})
            extension = {store: [] for store in histories}
            with zipfile.ZipFile(archive_path) as archive:
                with archive.open('train.csv') as binary:
                    with io.TextIOWrapper(binary, encoding='utf-8', newline='') as text:
                        reader = csv.DictReader(text)
                        if reader.fieldnames != ['id', 'date', 'store_nbr', 'family', 'sales', 'onpromotion']:
                            raise ValueError('source CSV schema mismatch')
                        for index, row in enumerate(reader):
                            if index % 65536 == 0:
                                checkpoint()
                            if row['family'] != 'BREAD/BAKERY' or row['store_nbr'] not in ('1', '2', '3'):
                                continue
                            if not '2016-01-01' <= row['date'] <= str(END):
                                continue
                            date, store = dt.date.fromisoformat(row['date']), int(row['store_nbr'])
                            if date in histories[store] or extension[store] and date <= extension[store][-1]:
                                raise ValueError('extension duplicate or unordered key')
                            histories[store][date] = finite_quantity(float(row['sales']))
                            extension[store].append(date)
            stat = archive_path.stat()
            if (stat.st_size, stat.st_mtime_ns, stat.st_dev, stat.st_ino) != before:
                raise ValueError('source changed during run')
            calendar = [START + dt.timedelta(days=i) for i in range((END-START).days+1)]
            snapshot = io.StringIO(newline='')
            writer = csv.writer(snapshot, lineterminator='\n')
            writer.writerow(['date', 'store_nbr', 'sales', 'observed'])
            quality = []
            for store, history in histories.items():
                for date in calendar:
                    value = history.get(date)
                    writer.writerow([str(date), store, '' if value is None else value, int(value is not None)])
                quality.append({'store': store, 'extension_observed_rows': len(extension[store]),
                    'extension_missing_dates': [str(date) for date in calendar if date > PREFIX_END and history.get(date) is None],
                    'extension_zero_rows': sum(history[date] == 0 for date in extension[store])})
            evidence.write_bytes('final-input-csv', snapshot.getvalue().encode('utf-8'))
            evidence.write_json('extension-quality', quality)
            predictions, fits, cells = [], [], []
            methods = ('weekly_naive', 'calendar_ridge')
            for origin in ORIGINS:
                for store in (1, 2, 3):
                    checkpoint()
                    # Pass only strict past to the forecaster, before attaching future actuals.
                    past = {date: value for date, value in histories[store].items() if date < origin}
                    pair = forecast_pair(past, origin)
                    fits.append({'store': store, **pair['model']})
                    rows = []
                    for forecast in pair['forecasts']:
                        target = dt.date.fromisoformat(forecast['date'])
                        actual = histories[store].get(target)
                        row = {'store': store, 'family': 'BREAD/BAKERY', 'origin': str(origin), **forecast,
                            'actual': actual, 'actual_missing_reason': None if actual is not None else 'target_not_observed'}
                        rows.append(row)
                        predictions.append(row)
                    paired = [row for row in rows if row['actual'] is not None and all(row[name] is not None for name in methods)]
                    cell = {'store': store, 'origin': str(origin), 'expected_targets': 14,
                        'target_missing': sum(row['actual'] is None for row in rows), 'paired_targets': len(paired), 'methods': {}}
                    for method in methods:
                        valid = [row for row in rows if row['actual'] is not None and row[method] is not None]
                        cumulative = None
                        if len(valid) == 14:
                            total_pred = sum(row[method] for row in rows)
                            total_actual = sum(row['actual'] for row in rows)
                            cumulative = {'predicted': total_pred, 'actual': total_actual,
                                'signed_error': total_pred-total_actual, 'absolute_error': abs(total_pred-total_actual)}
                        cell['methods'][method] = {'individual': metrics([(row[method], row['actual']) for row in valid]),
                            'paired': metrics([(row[method], row['actual']) for row in paired]),
                            'forecast_missing': sum(row[method] is None for row in rows), 'cumulative_14_days': cumulative}
                    cells.append(cell)
                    # Preserve every completed cell as a prefix if a later cell fails.
                    evidence.write_json(f'cell-{store}-{origin.month}', {'fit': fits[-1], 'cell': cell, 'predictions': rows})
                    print(json.dumps({'store': store, 'origin': str(origin), 'paired_targets': len(paired),
                        'MAE': {method: cell['methods'][method]['paired']['MAE'] for method in methods}}), flush=True)
            paired = [row for row in predictions if row['actual'] is not None and all(row[name] is not None for name in methods)]
            summary = {'status': 'complete', 'expected_targets': 126, 'paired_targets': len(paired),
                'aggregate': {name: metrics([(row[name], row['actual']) for row in paired]) for name in methods},
                'cells': cells, 'store_summaries': {str(store): {name: metrics([(row[name], row['actual'])
                    for row in paired if row['store'] == store]) for name in methods} for store in (1, 2, 3)},
                'origin_summaries': {str(origin): {name: metrics([(row[name], row['actual'])
                    for row in paired if row['origin'] == str(origin)]) for name in methods} for origin in ORIGINS},
                'performance_pass_claim': False, '2017_evaluation': True, 'future_promotion_used': False,
                'formal_permission': False, 'elapsed_seconds': time.monotonic()-started, 'OS_peak_private_or_pagefile_bytes': peak,
                'source_unchanged': True, 'calculator_pins': {name: pin(raw) for name, raw in source_raws.items()}}
            if any((REPO / name).read_bytes() != raw for name, raw in source_raws.items()):
                raise ValueError('calculator source changed during run')
            checkpoint()
            evidence.write_json('summary', summary)
            print(json.dumps({'status': 'complete', 'paired_targets': len(paired), 'aggregate': summary['aggregate'],
                              'elapsed_seconds': summary['elapsed_seconds'], 'peak_bytes': peak}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', required=True)
    args = parser.parse_args()
    run(args.records)
