"""One invented chunk's owned generation through full-fixture publication.

Seven owned children share a sampled outer clock. Local generator, saved
reader and publication budgets retain their original limits. Only one chunk
has observation payloads; the other 479 chunks are explicitly invented
metadata. Precomputed output and numerical pins precede the outer clock.
"""
from __future__ import annotations

import copy
from pathlib import Path
import time

from . import _anomaly_v03_outer_budget_link as link
from . import anomaly_v03_preformal_parent_git_identity as parent_git
from . import anomaly_v03_preformal_parent_git_blobs as parent_blobs
from . import anomaly_v03_preformal_generated_chain_budget as monitor
from . import anomaly_v03_preformal_owned_generated_attempt as generated
from . import anomaly_v03_preformal_saved_row_reread as reread
from . import anomaly_v03_preformal_saved_row_document_budget as document


ROOT = generated.ROOT
PREFIX = 'anomaly-v03-preformal-generation-publication-'
FORMAT = 'anomaly-v03-preformal-generation-publication-budget-v1'
SCOPE = 'one-invented-generated-chunk-plus-479-metadata-fixtures-to-full-draw-publication'
ROLES = ('producer', 'initial-reader', 'saved-reader', 'analysis', 'audit', 'writer', 'reader')
STAGES = ('preflight', 'producer', 'saved-reader', 'subset-read', 'publication', 'postflight')
LIMITS = {
    **document.chain.LIMITS,
    'wall_seconds': 1800,
    'directory_bytes': 321 * 1024**2,
    'directory_entries': 672,
    'directory_depth': 12,
}
LEAF_LIMITS = {
    'outer': (1024**2, 32, 2, 128 * 1024),
    'producer': (192 * 1024**2, 256, 12, 128 * 1024),
    'saved-reader': (32 * 1024**2, 256, 8, 64 * 1024),
    'publication': (96 * 1024**2, 128, 5, 128 * 1024),
}
SOURCE_NAMES = tuple(dict.fromkeys((
    'src/banto_ai/anomaly_v03_preformal_generation_publication_budget.py',
    *parent_git.SOURCE_FILES,
    *parent_blobs.SOURCE_FILES,
    *generated.SOURCE_FILES, *reread.SOURCE_FILES, *document.SOURCE_NAMES,
)))


def limits(value=None):
    result = dict(LIMITS if value is None else value)
    if set(result) != set(LIMITS):
        raise ValueError('generation-publication budget fields')
    for key, cap in LIMITS.items():
        number = result[key]
        valid = (type(number) in (int, float) and monitor.math.isfinite(number)
                 if key == 'wall_seconds' else type(number) is int)
        if not valid or number <= 0 or (number < cap if key.startswith('minimum_') else number > cap):
            raise ValueError('generation-publication limits may only tighten')
    return result


def _new_roots(outer_root, producer_root, reread_root, receipt_name):
    paths = generated.paths
    outer = paths.regular_path(Path(outer_root).absolute(), directory=True, missing=True)
    producer = generated._root(Path(producer_root).absolute(), missing=True)
    reader = paths.regular_path(Path(reread_root).absolute(), directory=True, missing=True)
    generated.v.safe_relative_path(receipt_name)
    if ('/' in receipt_name or '\\' in receipt_name or not receipt_name.startswith('trial-') or
            outer.parent != ROOT / 'artifacts' or not outer.name.startswith(PREFIX) or
            outer.name == PREFIX or reader.parent != ROOT / 'artifacts' or
            not reader.name.startswith(reread.PREFIX) or reader.name == reread.PREFIX):
        raise ValueError('dedicated generation-publication roots required')
    publication = paths.regular_path(document.OUTPUT_PARENT / receipt_name,
                                      directory=True, missing=True)
    roots = {'outer': outer, 'producer': producer,
             'saved-reader': reader, 'publication': publication}
    if len(set(roots.values())) != 4 or any(a.is_relative_to(b)
            for key, a in roots.items() for other, b in roots.items() if key != other):
        raise ValueError('generation-publication roots must be distinct and disjoint')
    if any(path.exists() for path in roots.values()):
        raise ValueError('generation-publication roots must all be new')
    return roots


class EnvelopeBudget(monitor.GeneratedChainBudget):
    phase_names = STAGES
    role_names = ROLES

    def __init__(self, roots, value=None):
        # The existing monitor initialization requires the exact generator
        # root. The versioned envelope then samples four fixed disjoint roots.
        super().__init__(roots['producer'])
        producer_identity = self.root_identity
        self.root = roots['outer']
        info = self.root.lstat()
        self.root_identity = (info.st_dev, info.st_ino)
        self.roots = dict(roots)
        self.limits = limits(value)
        self.identities = {'outer': self.root_identity, 'producer': producer_identity}
        self.leaf_last = {}
        self.leaf_maxima = {}
        self.checkpoint_counts = {name: 0 for name in STAGES}
        self.outputs = {}

    def require_stage(self, stage, root):
        if (stage not in ('producer', 'saved-reader', 'publication') or
                Path(root) != self.roots[stage] or self._thread is None or
                self._closed is not None or self._stop.is_set()):
            raise ValueError('stage must use its exact live outer-budget root')

    def _directory_observation(self):
        combined = {'directory_bytes': 0, 'directory_entries': 0, 'directory_depth': 0}
        observed = {}
        for name, root in self.roots.items():
            if not root.exists():
                if name in self.identities or name in ('outer', 'producer'):
                    raise monitor.resources.ResourceStop('envelope_root_missing')
                continue
            info = generated.paths.regular_path(root, directory=True).lstat()
            identity = (info.st_dev, info.st_ino)
            if not identity[1] or (name in self.identities and self.identities[name] != identity):
                raise monitor.resources.ResourceStop('envelope_root_changed')
            self.identities.setdefault(name, identity)
            cap, entries, depth, reserve = LEAF_LIMITS[name]
            if name == 'publication':
                tree = monitor.primitives.directory_snapshot(root, entries,
                    publication_roots=[root / 'published'])
                tree['directory_depth'] = document.chain.shared_budget._max_depth(root, entries, depth)
            else:
                tree = monitor._directory_snapshot(root, entries, depth, identity)
            if tree['directory_bytes'] + reserve > cap or tree['directory_entries'] + 2 > entries:
                raise monitor.resources.ResourceStop('envelope_' + name + '_directory_limit')
            observed[name] = tree
            combined['directory_bytes'] += tree['directory_bytes']
            combined['directory_entries'] += tree['directory_entries']
            combined['directory_depth'] = max(combined['directory_depth'], tree['directory_depth'])
        with self._state_lock:
            self.leaf_last = observed
            for name, tree in observed.items():
                peak = self.leaf_maxima.setdefault(name, dict(tree))
                for key, number in tree.items():
                    peak[key] = max(peak[key], number)
        return combined

    def checkpoint(self, phase):
        if phase not in STAGES or self._thread is None or self._closed is not None:
            raise ValueError('invalid generation-publication checkpoint')
        self.checkpoint_counts[phase] += 1
        if self.phase == phase and self.phase_log:
            self._observe()
            reason = self.probe()
            if reason is not None:
                raise monitor.resources.ResourceStop(reason)
        else:
            super().checkpoint(phase)

    def record_output(self, name, pin):
        if name not in document.chain.OUTPUTS or name in self.outputs or self._closed is not None:
            raise ValueError('generation-publication mapping output report')
        generated.copied.evidence._pin(pin)
        self.outputs[name] = copy.deepcopy(pin)

    def close(self):
        report = super().close()
        report.update(format=FORMAT + '-resource-budget', scope=SCOPE,
            root_measurement_scope='four fixed disjoint new roots; external manifest, prepared pins and metadata inputs excluded',
            roots={name: {'path': str(path),
                         'identity': list(self.identities.get(name, ())),
                         'leaf_limits': list(LEAF_LIMITS[name]),
                         'last': self.leaf_last.get(name),
                         'maxima': self.leaf_maxima.get(name)} for name, path in self.roots.items()},
            phase_checkpoint_counts=dict(self.checkpoint_counts),
            phase_history_scope='phase transitions; every checkpoint still samples and probes',
            reported_output_pins=copy.deepcopy(self.outputs),
            all_mapping_outputs_reported=set(self.outputs) == set(document.chain.OUTPUTS),
            all_seven_child_exits_reported=set(self.roles) == set(ROLES) and all(
                row['status'] == 'complete' and row['worker_exit_confirmed'] is True
                for row in self.roles.values()),
            complete_observation_campaign_verified=False,
            formal_50000_draw_budget_measured=False, smoke_capacity_twice_checked=False)
        report.pop('both_owned_exits_reported', None)
        raw = generated.v.canonical_json(report)
        if len(raw) > monitor.REPORT_MAX_BYTES:
            raise ValueError('generation-publication resource receipt bound')
        return report


def _source(revision, *, git_identity=None, git_blob=None):
    options = {}
    if git_identity is not None:
        options['git_identity'] = git_identity
    if git_blob is not None:
        options['git_blob'] = git_blob
    before = document._source_pins(revision, **options)
    for name in SOURCE_NAMES:
        raw = generated.observed._file(ROOT / name, 1024**2)
        committed = (generated.subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', revision + ':' + name],
            stderr=generated.subprocess.DEVNULL, timeout=10) if git_blob is None else
            git_blob(revision=revision, source_path=name,
                     expected_output_pin=generated.copied._pin(raw)))
        if type(committed) is not bytes or raw != committed:
            raise ValueError('generation-publication selected source changed: ' + name)
        before[name] = generated.copied._pin(raw)
    return before


def _subset(roots, manifest_path, manifest, manifest_pin, produced, read, budget):
    paths = {
        'result': roots['saved-reader'] / 'result.json',
        'rows': roots['saved-reader'] / 'rows.json',
        'budget': roots['saved-reader'] / 'resource-budget.json',
        'supervision': roots['saved-reader'] / 'owned-reader/supervision.json',
        'stdout': roots['saved-reader'] / 'owned-reader/worker/report.json',
        'manifest': manifest_path,
        'receipt': roots['producer'] / 'saved/receipt.json',
        'report': roots['producer'] / 'saved/report.json',
        'savepoint': roots['producer'] / 'saved/savepoint.json',
        'outer': roots['producer'] / 'owned-generator/result.json',
    }
    pins = {'result': read['result_pin'], 'rows': read['row_projection_pin'],
            'budget': read['resource_budget_pin'], 'supervision': read['reader_supervision_pin'],
            'stdout': read['child_stdout_pin'], 'manifest': manifest_pin,
            'outer': produced['result_pin'],
            **{name: manifest['output_pins']['saved/' + name + '.json']
               for name in ('receipt', 'report', 'savepoint')}}
    entry = {'expected_pins': copy.deepcopy(pins)}
    for name, path in paths.items():
        budget.checkpoint('subset-read')
        entry[name + '_raw'] = reread.pinned.read_pinned(path, pins[name],
            document.projection.coverage.RAW_LIMITS[name])
    expected = [{'chunk_index': manifest['chunk_index'], 'expected_pins': copy.deepcopy(pins)}]
    document.subset_projection.validate_subset_request([entry], expected)
    return [entry], expected, {name: {'path': str(path), 'pin': pins[name]} for name, path in paths.items()}


def run(*, outer_root, producer_root, reread_root, receipt_name,
        expected_manifest_pin, expected_revision, control_root,
        expected_control_pinset_pin, expected_input_pins, budget_limits=None,
        arithmetic_runtime_profiles=None, publication_runtime_profiles=None,
        saved_reader_runtime_profile=None, generation_runtime_profiles=None,
        parent_git_identity_policy=None, parent_git_blob_archive=False):
    """Execute one new engineering attempt; never adopt a formal evaluation."""
    roots = _new_roots(outer_root, producer_root, reread_root, receipt_name)
    generated.copied.evidence._digest(expected_revision, 40)
    profiles = document.chain.draw_bridge.validate_runtime_profiles(arithmetic_runtime_profiles,
                                                                    revision=expected_revision)
    publication_profiles = document.publication.validate_runtime_profiles(publication_runtime_profiles,
                                                                           revision=expected_revision)
    saved_reader_profile = reread.validate_runtime_profile(saved_reader_runtime_profile, revision=expected_revision)
    generation_profiles = generated.validate_runtime_profiles(generation_runtime_profiles, revision=expected_revision)
    git_policy = parent_git.validate(parent_git_identity_policy, revision=expected_revision, roots=roots)
    if type(parent_git_blob_archive) is not bool or (parent_git_blob_archive and git_policy is None):
        raise ValueError('parent blob archive requires explicit identity Job policy')
    generated.copied.evidence._pin(expected_manifest_pin)
    document._expected_pins(expected_input_pins)
    document.control_files.validate_request(control_root, expected_control_pinset_pin)
    value = limits(budget_limits)
    suffix = roots['producer'].name.removeprefix(generated.fixture.PREFIX)
    manifest_path = ROOT / ('artifacts/anomaly-v03-preformal-generated-pinsets-' + suffix) / 'pins.json'
    generated.paths.regular_path(manifest_path)
    roots['outer'].mkdir()
    roots['producer'].mkdir()
    budget = EnvelopeBudget(roots, value)
    critical = None
    result = {**document.chain.CLOSED, 'format': FORMAT, 'scope': SCOPE,
        'status': 'failed', 'stage': 'preflight', 'reason': None,
        'source_revision': expected_revision,
        'roots': {name: str(path) for name, path in roots.items()},
        'expected_manifest_pin': copy.deepcopy(expected_manifest_pin),
        'expected_input_pins': copy.deepcopy(expected_input_pins),
        'observation_chunks_generated_here': 0, 'observation_evaluations_verified_here': 0,
        'metadata_only_chunks': 479, 'complete_observation_campaign_verified': False,
        'same_outer_budget_generation_to_fresh_reader_measured': False,
        'observation_payload_reader_executed_inside_outer_budget': False,
        'subset_pin_origin': 'caller-captured-owned-stage-output-pins-inside-outer-clock',
        'precomputed_output_and_numerical_pins_inside_clock': False}
    if profiles is not None:
        result.update(arithmetic_runtime_profile_pins={role: copy.deepcopy(entry['expected_pin'])
            for role, entry in profiles.items()},
            arithmetic_runtime_profile_scope='analysis-and-audit-only-candidate',
            arithmetic_runtime_observation_checked=False)
    if publication_profiles is not None:
        result.update(publication_runtime_profile_pins={role: copy.deepcopy(entry['expected_pin'])
            for role, entry in publication_profiles.items()}, publication_runtime_observation_checked=False)
    if saved_reader_profile is not None:
        result.update(saved_reader_runtime_profile_pin=copy.deepcopy(saved_reader_profile['expected_pin']),
                      saved_reader_runtime_observation_checked=False)
    if generation_profiles is not None:
        result.update(generation_runtime_profile_pins={role: copy.deepcopy(entry['expected_pin'])
            for role, entry in generation_profiles.items()}, generation_runtime_observation_checked=False)
    git_receipts = {}
    blob_actor = None
    if parent_git_blob_archive:
        result.update(parent_git_blob_archive_enabled=True, parent_git_blobs_checked=False)
    if git_policy is not None:
        result.update(parent_git_identity_policy_pin=copy.deepcopy(git_policy['expected_pin']),
                      parent_git_identity_receipts=git_receipts, parent_git_identity_checked=False)
    try:
        budget.start()
        budget.checkpoint('preflight')
        if parent_git_blob_archive:
            blob_actor = parent_blobs.ParentBlobActor(git_policy, root=roots['outer'],
                checkout_root=ROOT, budget=budget,
                expected_requests=(*document.SOURCE_NAMES, *SOURCE_NAMES))
        identity = (lambda: parent_git.check(git_policy, phase='preflight', root=roots['outer'],
                    checkout_root=ROOT, budget=budget, receipts=git_receipts)) if git_policy is not None else None
        options = {'git_identity': identity} if identity is not None else {}
        if blob_actor is not None:
            options['git_blob'] = blob_actor.reader('preflight')
        before = _source(expected_revision, **options)
        if blob_actor is not None:
            blob_actor.verify(('preflight',))
        if git_policy is not None:
            parent_git.verify(git_policy, root=roots['outer'], checkout_root=ROOT,
                              budget=budget, receipts=git_receipts, phases=('preflight',))
        runtime = document.chain.platform_runtime.probe_runtime(ROOT)
        document.publication.check_runtime_profiles(publication_profiles, revision=expected_revision,
            source_pins=before, runtime=runtime)
        reread.check_runtime_profile(saved_reader_profile, revision=expected_revision,
                                    source_pins=before, runtime=runtime)
        generated.check_runtime_profiles(generation_profiles, revision=expected_revision,
                                        source_pins=before, runtime=runtime)
        raw = reread.pinned.read_pinned(manifest_path, expected_manifest_pin, reread.MAX_MANIFEST)
        manifest, snapshots = reread._manifest(raw, expected_manifest_pin, roots['producer'])
        if manifest['revision'] != expected_revision or manifest['recipe_id'] != generated.RECIPE:
            raise ValueError('precommitted generator manifest revision/recipe differs')
        result.update(source_pins_before=before, runtime_before=runtime,
                      output_bytes=manifest['output_bytes'], chunk_index=manifest['chunk_index'])
        result['stage'] = 'producer'
        local = link.LinkedBudget(monitor.GeneratedChainBudget(roots['producer']), budget,
            stage='producer', role_map={'generator': 'producer', 'reader': 'initial-reader'})
        local.start()
        try:
            generation_options = ({'generation_runtime_profiles': generation_profiles}
                                  if generation_profiles is not None else {})
            produced = generated.generate_and_read(roots['producer'],
                expected_pins=manifest['output_pins'], source_snapshots=snapshots,
                expected_revision=expected_revision, chunk_index=manifest['chunk_index'],
                outer_budget=local, **generation_options)
        finally:
            report = local.close()
            result['producer_budget_pin'] = document.chain._write_value(
                roots['producer'] / 'resource-budget.json', report, document.chain.MAX_CONTROL)
        result['producer_result_pin'] = produced['result_pin']
        if produced['status'] != 'verified' or report['passed'] is not True or not report['both_owned_exits_reported']:
            raise ValueError('owned generator and initial reader did not complete')
        if generation_profiles is not None:
            expected_generation_pins = {role: entry['expected_pin'] for role, entry in generation_profiles.items()}
            if (produced.get('generation_runtime_observation_checked') is not True or
                    produced.get('generation_runtime_profile_pins') != expected_generation_pins):
                raise ValueError('generation runtime observations missing or profile pins differ')
            result['generation_runtime_observation_checked'] = True
        result['observation_chunks_generated_here'] = 1
        result['stage'] = 'saved-reader'
        saved_reader_options = ({'saved_reader_runtime_profile': saved_reader_profile}
                                if saved_reader_profile is not None else {})
        read = reread.run_reread(roots['producer'], roots['saved-reader'],
            expected_manifest_pin=expected_manifest_pin, expected_outer_result_pin=produced['result_pin'],
            expected_revision=expected_revision, outer_budget=budget, **saved_reader_options)
        result['saved_reader_result_pin'] = read['result_pin']
        if read['status'] != 'verified' or read['verified_evaluations'] != 6:
            raise ValueError('owned physical saved reader did not complete')
        if saved_reader_profile is not None:
            if (read.get('saved_reader_runtime_observation_checked') is not True or
                    read.get('saved_reader_runtime_profile_pin') != saved_reader_profile['expected_pin']):
                raise ValueError('saved reader runtime observations missing or profile pin differs')
            result['saved_reader_runtime_observation_checked'] = True
        result['observation_evaluations_verified_here'] = 6
        result['observation_payload_reader_executed_inside_outer_budget'] = True
        result['stage'] = 'subset-read'
        entries, expected_subset, sources = _subset(roots, manifest_path, manifest,
            expected_manifest_pin, produced, read, budget)
        result.update(expected_observation_subset=expected_subset, subset_sources=sources)
        result['stage'] = 'publication'
        runtime_options = ({'arithmetic_runtime_profiles': profiles} if profiles is not None else {})
        if publication_profiles is not None:
            runtime_options['publication_runtime_profiles'] = publication_profiles
        published = document.run_saved_control_files_with_observation_subset(
            observation_subset=entries, expected_observation_subset=expected_subset,
            control_root=control_root, expected_control_pinset_pin=expected_control_pinset_pin,
            expected_mode='fixture', expected_input_pins=expected_input_pins,
            expected_revision=expected_revision, receipt_name=receipt_name, outer_budget=budget, **runtime_options)
        result['publication_result_pin'] = published['result_pin']
        if published['status'] != 'measured':
            raise ValueError('full-draw document publication did not complete')
        if profiles is not None:
            if published.get('arithmetic_runtime_observation_checked') is not True:
                raise ValueError('publication arithmetic runtime observations were not checked')
            expected_profile_pins = {role: entry['expected_pin'] for role, entry in profiles.items()}
            if published.get('arithmetic_runtime_profile_pins') != expected_profile_pins:
                raise ValueError('publication arithmetic runtime profile pins differ')
            result.update(arithmetic_runtime_profile_pins=copy.deepcopy(expected_profile_pins),
                arithmetic_runtime_profile_scope='analysis-and-audit-only-candidate',
                arithmetic_runtime_observation_checked=True)
        if publication_profiles is not None:
            expected_publication_pins = {role: entry['expected_pin'] for role, entry in publication_profiles.items()}
            if (published.get('publication_runtime_observation_checked') is not True or
                    published.get('publication_runtime_profile_pins') != expected_publication_pins):
                raise ValueError('publication runtime observations missing or profile pins differ')
            result.update(publication_runtime_observation_checked=True)
        result['stage'] = 'postflight'
        budget.checkpoint('postflight')
        result['final_saved_payload_recheck'] = reread._recheck_saved_outputs(
            roots['producer'], manifest['chunk_index'], manifest['output_pins'],
            _FinalCheckpoints(budget))
        for name, source in sources.items():
            budget.checkpoint('postflight')
            reread.pinned.read_pinned(Path(source['path']), source['pin'],
                document.projection.coverage.RAW_LIMITS[name])
        reread.recheck_runtime_profile(roots['saved-reader'], read)
        generated.recheck_runtime_profiles(roots['producer'], produced)
        identity = (lambda: parent_git.check(git_policy, phase='postflight', root=roots['outer'],
                    checkout_root=ROOT, budget=budget, receipts=git_receipts)) if git_policy is not None else None
        options = {'git_identity': identity} if identity is not None else {}
        if blob_actor is not None:
            options['git_blob'] = blob_actor.reader('postflight')
        if _source(expected_revision, **options) != before or document.chain.platform_runtime.probe_runtime(ROOT) != runtime:
            raise ValueError('generation-publication final source/runtime changed')
        if blob_actor is not None:
            blob_actor.verify(('preflight', 'postflight'))
            result['parent_git_blobs_checked'] = True
        if git_policy is not None:
            parent_git.verify(git_policy, root=roots['outer'], checkout_root=ROOT,
                              budget=budget, receipts=git_receipts)
            result['parent_git_identity_checked'] = True
        budget.checkpoint('postflight')
        result.update(status='measured', stage='complete', source_pins_after=before,
                      runtime_after=runtime, subset_final_disk_recheck_completed=True)
    except monitor.resources.ResourceStop as error:
        result['reason'] = error.reason
    except (ValueError, OSError, KeyError, TypeError, generated.subprocess.SubprocessError) as error:
        result.update(reason='generation_publication_rejected', error_type=type(error).__name__,
                      detail=str(error)[:500])
    except BaseException as error:
        result.update(reason='critical_generation_publication_failure', error_type=type(error).__name__)
        critical = error
    finally:
        if budget._thread is not None:
            try:
                report = budget.close()
                result['resource_budget_pin'] = document.chain._write_value(
                    roots['outer'] / 'resource-budget.json', report, document.chain.MAX_CONTROL)
                result.update(shared_budget_passed=report['passed'],
                    all_seven_child_exits_reported=report['all_seven_child_exits_reported'],
                    all_mapping_outputs_reported=report['all_mapping_outputs_reported'])
                if result['status'] == 'measured' and not (report['passed'] and
                        report['all_seven_child_exits_reported'] and report['all_mapping_outputs_reported']):
                    result.update(status='failed', reason=report['stop_reason'] or 'outer_completion_incomplete')
            except BaseException as error:
                result.update(status='failed', reason='outer_budget_close_failed',
                              budget_error_type=type(error).__name__)
                critical = critical or error
        result['same_outer_budget_generation_to_fresh_reader_measured'] = result['status'] == 'measured'
        if blob_actor is not None:
            result['parent_git_blob_archive_state'] = blob_actor.state()
        result['wall_seconds'] = time.monotonic() - budget.started_at
        result_pin = document.chain._write_value(roots['outer'] / 'result.json', result,
                                                 document.chain.MAX_CONTROL)
    if critical is not None:
        critical.receipt = roots['outer']
        raise critical
    return {**result, 'result_pin': result_pin}


class _FinalCheckpoints:
    def __init__(self, budget):
        self.budget = budget

    def checkpoint(self):
        self.budget.checkpoint('postflight')
