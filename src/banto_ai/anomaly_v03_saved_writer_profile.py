"""Bounded writer-only timing using pinned historical synthetic payloads.

Preparation and Git comparisons precede the unchanged writer supervisor clock.
This fixture does not run generation, bootstrap, a fresh reader or an outer
pipeline budget. Phase records survive a worker timeout as exclusive files.
"""
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from . import anomaly_v03_saved_row_document_publication as publication

ROOT = publication.ROOT
FORMAT = 'anomaly-v03-saved-writer-profile-v1'
SCOPE = 'historical-invented-payloads-writer-timing-only'
MODULE = 'src/banto_ai/anomaly_v03_saved_writer_profile.py'
TOOL = 'tools/preformal_saved_writer_profile_trial.py'
EVENT_MAX = 4096
JOURNAL_MAX = 64 * 1024
EVENT_COUNT = 128


class Journal:
    """A closed exclusive record is retained before entering each operation."""
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir()
        self.started = time.monotonic()
        self.count = self.bytes = 0
        self.stack = []

    def _event(self, event, label):
        value = {'format': FORMAT + '-phase', 'sequence': self.count,
                 'event': event, 'phase': label,
                 'elapsed_seconds': time.monotonic() - self.started}
        raw = publication.io.json_bytes(value)
        if (self.count >= EVENT_COUNT or len(raw) > EVENT_MAX or
                self.bytes + len(raw) > JOURNAL_MAX):
            raise ValueError('writer timing journal bound')
        publication.io._exclusive(self.root / ('%03d.json' % self.count), raw)
        self.count += 1
        self.bytes += len(raw)

    @contextmanager
    def phase(self, name):
        if not isinstance(name, str) or not name or '/' in name:
            raise ValueError('writer timing phase label')
        label = '.'.join((*self.stack, name))
        self._event('begin', label)
        self.stack.append(name)
        try:
            yield
        except BaseException:
            self._event('failed', label)
            raise
        else:
            self._event('end', label)
        finally:
            self.stack.pop()


def summarize(root):
    """Validate saved sequence/nesting, retaining open spans after hard stop."""
    paths = sorted(publication.io.regular_path(root, directory=True).iterdir())
    if len(paths) > EVENT_COUNT:
        raise ValueError('writer timing event count')
    records, spans, stack, pins = [], [], [], {}
    total, previous = 0, 0.0
    for index, path in enumerate(paths):
        if path.name != '%03d.json' % index:
            raise ValueError('writer timing sequence inventory')
        raw = publication.chain.draw_bridge.draw_budget._bounded_file(path, EVENT_MAX)
        total += len(raw)
        if total > JOURNAL_MAX:
            raise ValueError('writer timing journal bytes')
        value = publication.chain.draw_bridge.projection.v.strict_json(raw)
        if (set(value) != {'format', 'sequence', 'event', 'phase', 'elapsed_seconds'} or
                value['format'] != FORMAT + '-phase' or type(value['sequence']) is not int or
                value['sequence'] != index or not isinstance(value['phase'], str) or
                not value['phase'] or '/' in value['phase'] or
                type(value['elapsed_seconds']) not in (int, float) or
                not math.isfinite(value['elapsed_seconds']) or
                value['elapsed_seconds'] < previous):
            raise ValueError('writer timing event binding')
        previous = value['elapsed_seconds']
        if value['event'] == 'begin':
            if stack and not value['phase'].startswith(stack[-1]['phase'] + '.'):
                raise ValueError('writer timing nesting')
            stack.append(value)
        elif value['event'] in ('end', 'failed'):
            if not stack or stack[-1]['phase'] != value['phase']:
                raise ValueError('writer timing span closure')
            start = stack.pop()
            spans.append({'phase': value['phase'], 'status': value['event'],
                          'seconds': previous - start['elapsed_seconds']})
        else:
            raise ValueError('writer timing event kind')
        pins[path.name] = publication._pin(raw)
        records.append(value)
    return {'event_pins': pins, 'events': records, 'spans': spans,
            'open_phases': [row['phase'] for row in stack], 'bytes': total}


def _source(revision, names):
    pins = publication.chain._source_pins(revision)
    for name in sorted(set(names) | {MODULE, TOOL}):
        publication.chain.draw_bridge.projection.v.safe_relative_path(name)
        if not name.startswith(('src/banto_ai/', 'tools/')) or not name.endswith('.py'):
            raise ValueError('writer timing selected source path')
        raw = publication.chain.draw_bridge.draw_budget._bounded_file(ROOT / name, 1024**2)
        committed = subprocess.check_output(['git', '-C', str(ROOT), 'show', revision + ':' + name],
                                             stderr=subprocess.DEVNULL, timeout=10)
        if raw != committed:
            raise ValueError('writer timing source differs from Git: ' + name)
        pins[name] = publication._pin(raw)
    return pins


def worker_main(argv):
    try:
        if len(argv) != 3:
            raise ValueError('writer timing worker arguments')
        path, size, digest = argv
        request_path = Path(path).absolute()
        pin = {'bytes': int(size), 'sha256': digest}
        request = publication.chain.draw_bridge.projection.v.strict_json(
            publication._read(request_path, pin, publication.REQUEST_MAX))
        if (request['format'] != FORMAT + '-request' or request['scope'] != SCOPE or
                request['role'] != 'writer' or MODULE not in request['source_pins'] or
                TOOL not in request['source_pins'] or
                request_path != Path(request['receipt_root']) / 'writer/request.json'):
            raise ValueError('writer timing worker ownership')
        journal = Journal(request_path.parent / 'phases')
        with journal.phase('writer'):
            result, files = publication._perform(request, phase=journal.phase)
            if {name: publication._pin(raw) for name, raw in files.items()} != request['payload_pins']:
                raise ValueError('writer timing framed payload pins')
        result.update(format=FORMAT, scope=SCOPE, status='verified', request_pin=pin,
            numerical_source_revision=request['source_revision'],
            worker_source_revision=request['worker_source_revision'],
            source_pins=request['source_pins'], payload_pins=request['payload_pins'],
            formal_permission=False, registered_data_read=False,
            independent_s6_complete=False, numeric_draws_recomputed=False,
            fresh_reader_started=False, full_end_to_end_budget_measured=False,
            process={**publication.observed.creation_observation(os.getpid()), 'parent_pid': os.getppid()})
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'rejected', 'detail': str(error)[:500], 'formal_permission': False}))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def run(*, source_root, expected_request_pin, expected_worker_revision, receipt_name):
    source_root = Path(source_root).absolute()
    root = publication.OUTPUT_PARENT / receipt_name
    if (source_root.parent != publication.OUTPUT_PARENT or not source_root.name.startswith('trial-') or
            Path(receipt_name).name != receipt_name or not receipt_name.startswith('trial-') or root == source_root):
        raise ValueError('writer timing root ownership')
    source_path = source_root / 'writer/request.json'
    historical_raw = publication._read(source_path, expected_request_pin, publication.REQUEST_MAX)
    historical = publication.chain.draw_bridge.projection.v.strict_json(historical_raw)
    if (historical['format'] != publication.FORMAT + '-request' or historical['role'] != 'writer' or
            historical['receipt_root'] != str(source_root) or
            historical['publication_root'] != str(source_root / 'published') or
            set(historical['payload_source_pins']) != set(publication.PAYLOAD_LIMITS) or
            set(historical['projection_input_pins']) != set(publication.chain.draw_bridge.projection.analysis.INPUT_LIMITS)):
        raise ValueError('writer timing historical request binding')
    sources = _source(expected_worker_revision, historical['source_pins'])
    # Copy only previously pinned inputs. Historical numerical claims are kept.
    inputs = {name: (historical['payload_source_pins'][name], maximum)
              for name, maximum in publication.PAYLOAD_LIMITS.items()}
    inputs.update({'input.json': (historical['input_pin'], 512 * 1024),
                   'projection.json': (historical['projection_pin'], 8 * 1024**2)})
    inputs.update({'inputs/' + Path(name).name: (pin, publication.chain.draw_bridge.projection.analysis.INPUT_LIMITS[name])
                   for name, pin in historical['projection_input_pins'].items()})
    captured = {name: publication._read(source_root / name, pin, maximum)
                for name, (pin, maximum) in inputs.items()}
    root.mkdir()
    (root / 'inputs').mkdir()
    target = root / 'writer'
    target.mkdir()
    for name, raw in captured.items():
        publication.io._exclusive(root / name, raw)
    publication.io._exclusive(root / 'historical-request.json', historical_raw)
    request = {**historical, 'format': FORMAT + '-request', 'scope': SCOPE,
               'receipt_root': str(root), 'publication_root': str(root / 'published'),
               'worker_source_revision': expected_worker_revision, 'source_pins': sources,
               'historical_request_pin': expected_request_pin, 'historical_root': str(source_root)}
    request_raw = publication.io.json_bytes(request)
    if len(request_raw) > publication.REQUEST_MAX:
        raise ValueError('writer timing request bytes')
    request_pin = publication._pin(request_raw)
    publication.io._exclusive(target / 'request.json', request_raw)
    parent = Journal(root / 'parent-phases')
    launch = {}
    def boundary():
        with parent.phase('supervisor_boundary'):
            publication._read(target / 'request.json', request_pin, publication.REQUEST_MAX)
            publication._source_recheck(sources)
    def started(process):
        with parent.phase('original_handle_identity'):
            launch.update(publication.observed.creation_observation(process.pid, process._handle))
            publication.io._exclusive(target / 'launch.json', publication.io.json_bytes(launch))
    def runtime():
        with parent.phase('runtime_probe'):
            return publication.supervisor.resources.probe_runtime(ROOT)
    bootstrap = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
                 'from banto_ai.anomaly_v03_saved_writer_profile import worker_main;'
                 'raise SystemExit(worker_main(sys.argv[1:]))')
    argv = [sys.executable, '-I', '-S', '-B', '-c', bootstrap, str(ROOT / 'src'),
            str(target / 'request.json'), str(request_pin['bytes']), request_pin['sha256']]
    try:
        with publication.platform._platform_scope(), parent.phase('supervisor'):
            report = publication.supervisor.supervise(argv, ROOT, target / 'worker', publication.LIMITS,
                boundary=boundary, on_started=started, runtime_probe=runtime)
    except publication.supervisor.UnreapedWorker as error:
        publication.chain._write_value(target / 'supervision.json', error.report, publication.chain.MAX_CONTROL)
        error.receipt = root
        raise
    report_pin = publication.chain._write_value(target / 'supervision.json', report, publication.chain.MAX_CONTROL)
    complete = (report['status'] == 'complete' and report['worker_exit_confirmed'] is True and
                report['exit_code'] == 0 and not report['observation_errors'] and report['worker_pid'] == launch.get('pid'))
    reply = None
    if complete:
        reply = publication.chain.draw_bridge.projection.v.strict_json(
            publication._read(target / 'worker/report.json', report['output'], publication.LIMITS['output_bytes']))
        publication.chain.document_bridge._same_fields(reply, {
            'format': FORMAT, 'scope': SCOPE, 'status': 'verified', 'request_pin': request_pin,
            'numerical_source_revision': historical['source_revision'], 'worker_source_revision': expected_worker_revision,
            'source_pins': sources, 'payload_pins': historical['payload_pins'],
            'formal_permission': False, 'registered_data_read': False, 'independent_s6_complete': False,
            'numeric_draws_recomputed': False, 'fresh_reader_started': False, 'full_end_to_end_budget_measured': False,
            'process': {**launch, 'parent_pid': os.getpid()}}, 'writer timing reply')
    _source(expected_worker_revision, sources)
    journal = summarize(target / 'phases') if (target / 'phases').exists() else None
    result = {'format': FORMAT, 'scope': SCOPE, 'status': 'verified' if complete else 'failed',
              'reason': report['stop_reason'], 'numerical_source_revision': historical['source_revision'],
              'worker_source_revision': expected_worker_revision, 'source_pins': sources,
              'historical_request_pin': expected_request_pin, 'historical_root': str(source_root),
              'request_pin': request_pin, 'supervision_pin': report_pin, 'limits': dict(publication.LIMITS),
              'worker_exit_confirmed': report['worker_exit_confirmed'], 'worker': launch,
              'copied_input_pins': {name: pin for name, (pin, _) in inputs.items()},
              'worker_phases': journal, 'parent_phases': summarize(root / 'parent-phases'),
              'reply': reply, 'complete_marker_exists': (root / 'published/.complete').exists(),
              'fresh_reader_started': False, 'formal_permission': False, 'registered_data_read': False,
              'independent_s6_complete': False, 'numeric_draws_recomputed': False,
              'full_end_to_end_budget_measured': False, 'source_runtime_closure_verified': False,
              'preparation_inside_writer_clock': False, 'outer_budget_measured': False}
    result_pin = publication.chain._write_value(root / 'result.json', result, publication.chain.MAX_CONTROL)
    return {**result, 'result_pin': result_pin}
