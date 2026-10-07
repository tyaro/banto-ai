"""Owned generation and separate reading of one invented registered-format chunk.

The fixed hand-normal recipe exercises storage and consumer boundaries only.  A
holdout identity is a schema marker; no registered seed or actual observation
is generated or read here.  A caller computes and retains output pins before
the owned generator is launched.  None of these facts grants formal credit.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from . import _anomaly_v03_contract as contract
from . import _anomaly_v03_io as io
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_inference_audit as arithmetic
from . import anomaly_v03_ledger_audit as ledger
from . import anomaly_v03_materializer as materializer
from . import anomaly_v03_platform_fixture as platform
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_preformal_campaign_child_context as child_context
from . import anomaly_v03_preformal_owned_saved_attempt as copied
from . import anomaly_v03_process_supervisor as supervisor
from . import anomaly_v03_reader_evidence as observed
from . import anomaly_v03_registered_saved_attempt_fixture as fixture
from . import anomaly_v03_registered_saved_summary as saved
from . import anomaly_v03_runner as runner
from . import anomaly_v03_slices as slices


ROOT = Path(__file__).resolve().parents[2]
RECIPE = 'hand-normal-v1'
FORMAT = 'anomaly-v03-preformal-owned-generated-attempt-v1'
INVOCATION = 'anomaly-v03-preformal-owned-generated-invocation-v1'
CAMPAIGN_INVOCATION = 'anomaly-v03-preformal-owned-generated-invocation-v2'
CAMPAIGN_FORMAT = 'anomaly-v03-preformal-owned-generated-attempt-v2'
CHAIN_FORMAT = 'anomaly-v03-preformal-owned-generated-two-role-v1'
BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
             'from banto_ai.anomaly_v03_preformal_owned_generated_attempt import worker_main;'
             'raise SystemExit(worker_main(sys.argv[1:]))')
LIMITS = {'wall_seconds': 360, 'private_bytes': 768 * 1024**2,
          'output_bytes': 1024**2}
MAX_INVOCATION = 256 * 1024
# The native successful probe had a longest path of 245 characters.  This is
# a conservative fixture spelling bound, not a proof of all Windows path APIs.
MAX_NATIVE_PATH = 245
SOURCE_FILES = tuple(dict.fromkeys((
    *copied.SOURCE_FILES,
    'src/banto_ai/anomaly_v03_preformal_campaign_child_context.py',
    'src/banto_ai/anomaly_v03_preformal_owned_generated_attempt.py',
    'src/banto_ai/anomaly_v03_preformal_generated_chain_budget.py',
    'tools/preformal_owned_generated_trial.py',
    'src/banto_ai/anomaly_v03_materializer.py',
    'src/banto_ai/anomaly_v03_runner.py',
    'src/banto_ai/anomaly_v03_episodes.py',
    'src/banto_ai/anomaly_v03_scoring.py',
    'src/banto_ai/anomaly_v03_slices.py',
    'src/banto_ai/anomaly_v03_ledger_audit.py',
    'src/banto_ai/anomaly_v03_inference_audit.py',
)))
SNAPSHOT_FILES = (
    'src/banto_ai/anomaly_v03_preformal_owned_generated_attempt.py',
    'src/banto_ai/anomaly_v03_materializer.py',
)


def validate_runtime_profiles(profiles, *, revision):
    if profiles is None:
        return None
    from . import anomaly_v03_role_runtime_observation as observation
    v.require(type(profiles) is dict and set(profiles) == {'producer', 'initial-reader'},
              'generation runtime profile role inventory')
    retained = {}
    for role, entry in profiles.items():
        v.require(type(entry) is dict and set(entry) == {'raw', 'expected_pin'},
                  'generation runtime profile entry fields')
        value = observation.load_profile(entry['raw'], entry['expected_pin'], root=ROOT, role=role)
        v.require(value['source_revision'] == revision, 'generation runtime profile revision differs')
        retained[role] = {'raw': entry['raw'], 'expected_pin': copy.deepcopy(entry['expected_pin'])}
    return retained


def check_runtime_profiles(profiles, *, revision, source_pins, runtime, reader_source_pins=None,
                           reader_source_names=None):
    retained = validate_runtime_profiles(profiles, revision=revision)
    if retained is None:
        return None
    from . import anomaly_v03_role_runtime_observation as observation
    for role, entry in retained.items():
        value = observation.load_profile(entry['raw'], entry['expected_pin'], root=ROOT, role=role)
        required = SOURCE_FILES if role == 'producer' else (
            copied.SOURCE_FILES if reader_source_names is None else reader_source_names)
        selected = reader_source_pins if role == 'initial-reader' and reader_source_pins is not None else source_pins
        v.require(value['runtime'] == runtime, 'generation runtime profile tuple differs')
        v.require(all(name in selected and value['source_files'].get(name) == selected[name]
                      for name in required), 'generation runtime profile selected Git source differs')
    return retained


def _runtime_reply(reply, *, role, target, profiles, input_pin, process):
    if profiles is None:
        v.require('runtime_observation' not in reply, 'unexpected generation runtime observation')
        return None
    from . import anomaly_v03_role_runtime_observation as observation
    entry = profiles[role]
    return observation.verify_receipt(reply.get('runtime_observation'), root=target, source_root=ROOT,
        role=role, profile_raw=entry['raw'], profile_pin=entry['expected_pin'], input_pin=input_pin, process=process)


def recheck_runtime_profiles(root, result):
    """Reopen profile/invocation/stdout/phases after both roles, without replay."""
    if 'generation_runtime_profile_pins' not in result:
        return
    from . import anomaly_v03_role_runtime_observation as observation
    for role, profile_pin in result['generation_runtime_profile_pins'].items():
        prefix = 'generator' if role == 'producer' else 'reader'
        target = Path(root) / ('owned-generator' if role == 'producer' else 'owned-reader')
        copied.pinned.read_pinned(target / 'inventory-profile.json', profile_pin, observation.MAX_PROFILE)
        copied.pinned.read_pinned(target / 'invocation.json', result[prefix + '_invocation_pin'], MAX_INVOCATION)
        reply = v.strict_json(copied.pinned.read_pinned(target / 'worker/report.json',
            result[prefix + '_stdout_pin'], (LIMITS if role == 'producer' else copied.READER_LIMITS)['output_bytes']))
        receipt = result['runtime_observations'][role]
        v.require(reply.get('runtime_observation') == receipt, 'generation runtime receipt changed')
        for phase in ('before', 'after'):
            copied.pinned.read_pinned(target / (role + '-runtime-' + phase + '.json'), receipt[phase + '_pin'],
                               observation.MAX_RECEIPT)


def _root(root, *, missing=False):
    root = paths.regular_path(Path(root), directory=True, missing=missing)
    v.require(root.parent == ROOT / 'artifacts' and
              root.name.startswith(fixture.PREFIX),
              'dedicated invented generator root required')
    return root


def _outputs(root, chunk_index):
    v.require(type(chunk_index) is int and 0 <= chunk_index < 480,
              'invented generator chunk index')
    _, physical = fixture._names(chunk_index, 1)
    names = copied._output_names(physical)
    v.require(len(names) == 22 and len(set(names.values())) == 22,
              'exact generated output inventory')
    for relative in names.values():
        v.safe_relative_path(relative)
        v.require(len(str(root / relative)) <= MAX_NATIVE_PATH,
                  'generated output path exceeds native probe bound')
    return names


def _source(expected_revision, *, git_identity=None, git_blob=None):
    """Selected raw working/Git source check; this is not source closure."""
    copied.evidence._digest(expected_revision, 40)
    v.require(git_identity is None or callable(git_identity),
              'generator Git identity callback must be callable')
    v.require(git_blob is None or callable(git_blob),
              'generator Git blob callback must be callable')
    if git_identity is None:
        head = subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL, timeout=10)
        v.require(type(head) is bytes and head.strip() == expected_revision.encode(),
                  'selected generator revision changed')
        dirty = subprocess.check_output(
            ['git', '-c', 'core.fsmonitor=false', '-C', str(ROOT), 'status',
             '--porcelain', '--untracked-files=normal'],
            stderr=subprocess.DEVNULL, timeout=10)
    else:
        identity = git_identity()
        v.require(type(identity) is dict and set(identity) == {'head', 'status'},
                  'generator Git identity raw inventory')
        head, dirty = identity['head'], identity['status']
    v.require(type(head) is bytes and type(dirty) is bytes,
              'generator Git identity raw bytes')
    v.require(head.strip() == expected_revision.encode(), 'selected generator revision changed')
    v.require(not dirty, 'clean generator checkout required')
    rows = []
    for name in SOURCE_FILES:
        working = observed._file(ROOT / name, 1024**2)
        committed = (subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', expected_revision + ':' + name],
            stderr=subprocess.DEVNULL, timeout=10) if git_blob is None else
            git_blob(revision=expected_revision, source_path=name,
                     expected_output_pin=copied._pin(working)))
        v.require(type(committed) is bytes and working == committed,
                  'selected generator source changed: ' + name)
        rows.append({'path': name, 'pin': copied._pin(working)})
    return {'revision': expected_revision, 'selected_files': rows,
            'scope': 'selected-working-git-raw-only-not-source-closure'}


def _validated_snapshots(value, expected_revision, *, git_blob=None):
    """Bind the two selected executable source bytes to working and Git bytes."""
    v.require(type(value) is dict and set(value) == {expected_revision},
              'source snapshot revision binding')
    v.require(git_blob is None or callable(git_blob),
              'generator snapshot Git blob callback must be callable')
    copied._source_snapshots(value)
    rows = value[expected_revision]
    v.require(type(rows) is dict and set(rows) == set(SNAPSHOT_FILES),
              'actual generator/materializer source snapshots required')
    for name in SNAPSHOT_FILES:
        raw = rows[name]
        working = observed._file(ROOT / name, 1024**2)
        committed = (subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', expected_revision + ':' + name],
            stderr=subprocess.DEVNULL, timeout=10) if git_blob is None else
            git_blob(revision=expected_revision, source_path=name,
                     expected_output_pin=copied._pin(working)))
        v.require(type(committed) is bytes and raw == working == committed,
                  'source snapshot working/Git bytes changed: ' + name)
    return paths.Checkout(ROOT, expected_revision,
                          tuple((name, rows[name]) for name in SNAPSHOT_FILES))


def _normal():
    """Five fixed finite values at hand-ordered coordinates; no RNG or seed."""
    for equipment in contract.EQUIPMENT:
        for sample in range(9000):
            yield equipment, sample, {
                'motor_current': 10.0, 'motor_temperature': 40.0,
                'conveyor_speed': 5.0, 'vibration_feature': 1.0,
                'load_proxy': 50.0}


def _primary(evaluation):
    metrics = evaluation['metrics']
    counts = {}
    for kind in arithmetic.METRICS[:5]:
        item = metrics[kind]
        counts[kind] = list(arithmetic.counts(
            [item['numerator'], item['denominator']], kind))
    for item, kind in zip(metrics['availability'], arithmetic.AVAILABILITY):
        value = item['metric']
        counts[kind] = list(arithmetic.counts(
            [value['numerator'], value['denominator']], kind))
    histogram = [0] * 5
    for incident in evaluation['incidents']:
        if incident['causal_detected']:
            histogram[int(incident['delay_seconds']) - 1] += 1
    return {'counts': counts,
            'effective_clean_seconds': metrics['effective_clean_seconds'],
            'delay_histogram': histogram}


def build_invented_output_bytes(root, *, chunk_index=0, recipe_id=RECIPE,
                                source_snapshots, before_evaluations=None):
    """Build deterministic bytes for caller-held prelaunch pins.

    The default path writes nothing.  In the child, the callback persists and
    rereads the twelve dataset inputs before evaluations.  The parent wrapper
    never calls this function or derives missing pins.  A caller must save the
    computed 22-file pinset outside the target root before launching the child.
    """
    v.require(recipe_id == RECIPE, 'unknown invented generator recipe')
    root = _root(root, missing=True)
    names = _outputs(root, chunk_index)
    v.require(type(source_snapshots) is dict and len(source_snapshots) == 1,
              'one caller source snapshot revision required')
    revision = next(iter(source_snapshots))
    checkout = _validated_snapshots(source_snapshots, revision)
    identities = v.evaluation_inventory('holdout')[chunk_index * 6:chunk_index * 6 + 6]
    v.require(len(identities) == 6, 'six invented schema identities')
    pair = materializer._build_pair(identities[0], _normal())
    materializer.validate_pair(*pair)
    datasets = {v.strict_json(dataset.identity_json)['dataset_id']: dataset.files()
                for dataset in pair}
    v.require(len(datasets) == 2, 'two invented strata datasets')
    payloads = {}
    for identity in identities:
        files = datasets[identity['dataset_id']]
        for kind, filename in materializer.INPUT_FILES.items():
            payloads[saved._payload_path(identity, kind)] = files[filename]
    v.require(len(payloads) == 12, 'shared dataset input inventory')
    if before_evaluations is not None:
        v.require(callable(before_evaluations), 'dataset readback callback')
        readback = before_evaluations(dict(payloads))
        v.require(type(readback) is dict and set(readback) == set(payloads),
                  'exact saved dataset readback inventory')
        copied._same({name: copied._pin(raw) for name, raw in readback.items()},
                     {name: copied._pin(raw) for name, raw in payloads.items()},
                     'saved dataset readback bytes')
        payloads = readback
        for identity in identities:
            files = datasets[identity['dataset_id']]
            for kind, filename in materializer.INPUT_FILES.items():
                files[filename] = payloads[saved._payload_path(identity, kind)]
    registry_raw = observed._file(
        ROOT / 'examples/configs/anomaly-v03-freeze-registry.json',
        saved.MAX_REGISTRY)
    registry_pin = copied._pin(registry_raw)
    v.require(registry_pin['sha256'] == v.REGISTRY_RAW_SHA256,
              'frozen invented registry bytes')
    savepoint_raw = v.canonical_json({
        'format': fixture.SAVEPOINT_FORMAT, 'mode': saved.MODE,
        'invented_only': True, 'campaign_completed': False,
        'actual_registered_observations_read': False,
        'run_root': str(root / 'run-root'), 'chunk_index': chunk_index})
    savepoint_pin = copied._pin(savepoint_raw)
    slots, rows = [], []
    for identity in identities:
        files = datasets[identity['dataset_id']]
        evaluation = runner.compute_evaluation(identity, files, checkout)
        evaluation_raw = v.canonical_json(evaluation)
        logical = saved._payload_path(identity)
        payloads[logical] = evaluation_raw
        hashes = evaluation['input_hashes']
        outcome = ('inconclusive' if any(
            profile['status'] != 'calibrated' for profile in evaluation['profiles'])
            else 'success')
        slots.append({'identity': identity, 'status': outcome,
                      'profile_status': 'inconclusive' if outcome == 'inconclusive'
                      else 'calibrated', 'input_hashes': hashes,
                      'evaluation_sha256': copied._pin(evaluation_raw)['sha256']})
        audited = ledger.audit_evaluation(evaluation)
        slice_counts = slices.summarize_evaluation(
            evaluation, {'identity': identity, 'evaluation_outcome': outcome,
                         'ledger_audit': audited}, reported_only=True)['counts']
        rows.append({'identity': identity, 'evaluation_outcome': outcome,
                     'evaluation_pin': copied._pin(evaluation_raw),
                     'input_hashes': hashes, 'primary': _primary(evaluation),
                     'slices': slice_counts})
    v.require(len(payloads) == 18 and set(payloads) == set(names) - set(copied.SAVED),
              'shared dataset input and evaluation inventory')
    receipt_raw = v.canonical_json({
        'format': saved.RECEIPT_FORMAT, 'mode': saved.MODE,
        'invented_only': True, 'registry_pin': registry_pin,
        'savepoint_pin': savepoint_pin, 'chunk_index': chunk_index,
        'attempts': [{'attempt': 1, 'state': 'complete', 'failure': None,
                      'evaluations': slots}]})
    report_raw = v.canonical_json({
        'format': saved.REPORT_FORMAT, 'mode': saved.MODE,
        'invented_only': True, 'registry_pin': registry_pin,
        'receipt_pin': copied._pin(receipt_raw),
        'savepoint_pin': savepoint_pin, 'chunk_index': chunk_index,
        'attempt': 1, 'rows': rows,
        'payload_pins': {name: copied._pin(raw)
                         for name, raw in payloads.items()}})
    output = {**payloads,
              'saved/savepoint.json': savepoint_raw,
              'saved/registry.json': registry_raw,
              'saved/receipt.json': receipt_raw,
              'saved/report.json': report_raw}
    v.require(set(output) == set(names), 'exact generated output keys')
    total = 0
    for logical, raw in output.items():
        v.require(type(raw) is bytes and 0 < len(raw) <= copied._maximum(logical),
                  'generated file byte bound')
        total += len(raw)
    v.require(total <= saved.MAX_TOTAL, 'generated total byte bound')
    return output


def _validate_pins(names, expected_pins):
    v.require(type(expected_pins) is dict and set(expected_pins) == set(names),
              'exact externally retained generator pins required')
    total = 0
    for logical, pin in expected_pins.items():
        copied.evidence._pin(pin)
        v.require(0 < pin['bytes'] <= copied._maximum(logical),
                  'generator output pin byte bound')
        total += pin['bytes']
    v.require(total <= saved.MAX_TOTAL, 'generator output pin total bound')
    v.require(expected_pins['saved/registry.json']['sha256'] ==
              v.REGISTRY_RAW_SHA256, 'frozen generator registry pin required')


def _preflight(root, chunk_index, expected_pins):
    names = _outputs(root, chunk_index)
    _validate_pins(names, expected_pins)
    for name in ('saved', 'run-root', 'owned-generator', 'owned-reader'):
        paths.regular_path(root / name, directory=True, missing=True)
        v.require(not (root / name).exists(),
                  'generator outputs and role roots must be new')
    return names


def _generate_attempt(request, root, *, git_identity=None, git_blob=None):
    """The original generation/save/readback operation, performed once."""
    campaign_mode = 'campaign_context' in request
    source_options = {}
    if git_identity is not None:
        source_options['git_identity'] = git_identity
    if git_blob is not None:
        source_options['git_blob'] = git_blob
    names = _outputs(root, request['chunk_index'])
    copied._same(request['output_names'], names,
                 'generator output names')
    external = request['external_pins']
    _validate_pins(names, external)
    snapshots = copied._decode_source_snapshots(request['source_snapshots'])
    _validated_snapshots(snapshots, request['source_revision'],
                         **({'git_blob': git_blob} if git_blob is not None else {}))
    source_before = _source(request['source_revision'], **source_options)
    runtime_before = runtime.probe_runtime(ROOT)
    copied._same(source_before, request['source'], 'generator source before')
    copied._same(runtime_before, request['runtime'], 'generator runtime before')
    for name in ('saved', 'run-root'):
        v.require(not (root / name).exists(), 'new generator output roots')
    process = observed.creation_observation(os.getpid())

    def save_and_read_dataset_inputs(inputs):
        v.require(len(inputs) == 12 and all(
            name.startswith('datasets/') for name in inputs),
            'twelve shared dataset inputs before evaluations')
        (root / 'run-root').mkdir()
        for logical, data in sorted(inputs.items()):
            copied._same(copied._pin(data), external[logical],
                         'predeclared dataset input pin')
            target = root / names[logical]
            target.parent.mkdir(parents=True, exist_ok=True)
            io._exclusive(target, data)
        copied._inventory(root / 'run-root',
                          [names[logical].removeprefix('run-root/')
                           for logical in inputs])
        return {logical: copied._checked_file(
            root, names[logical], external[logical],
            copied._maximum(logical)) for logical in sorted(inputs)}

    output = build_invented_output_bytes(
        root, chunk_index=request['chunk_index'],
        recipe_id=request['recipe_id'], source_snapshots=snapshots,
        before_evaluations=save_and_read_dataset_inputs)
    pins = {name: copied._pin(value) for name, value in output.items()}
    copied._same(pins, external, 'externally predeclared generated bytes')
    (root / 'saved').mkdir()
    for logical, relative in sorted(names.items()):
        if logical.startswith('datasets/'):
            continue
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        io._exclusive(target, output[logical])
    copied._check_outputs(root, names, external)
    source_after = _source(request['source_revision'], **source_options)
    runtime_after = runtime.probe_runtime(ROOT)
    copied._same(source_after, source_before, 'generator source after')
    copied._same(runtime_after, runtime_before, 'generator runtime after')
    reply = {'format': (CAMPAIGN_FORMAT if campaign_mode else FORMAT),
             'status': 'generated',
             'invocation_id': request['invocation_id'],
             'process': {'pid': os.getpid(), 'parent_pid': os.getppid(),
                         'start_token': process['start_token']},
             'recipe_id': RECIPE, 'output_pins': external,
             'output_file_count': len(names), 'output_bytes': sum(
                 pin['bytes'] for pin in external.values()),
             'source_before': source_before, 'source_after': source_after,
             'runtime_before': runtime_before, 'runtime_after': runtime_after,
             'invented_generation_executed': True,
             'registered_seed_consumed': False,
             'actual_registered_observations_read': False,
             'formal_permission': False}
    if campaign_mode:
        reply['campaign_context'] = copy.deepcopy(request['campaign_context'])
    return reply


def worker_main(argv):
    """Generate bytes in an isolated owned child from recipe and prelaunch pins."""
    try:
        v.require(len(argv) == 2, 'generator worker arguments')
        path = paths.regular_path(Path(argv[0]))
        raw = observed._file(path, MAX_INVOCATION)
        v.require(copied._pin(raw)['sha256'] == argv[1],
                  'generator invocation pin')
        request = v.strict_json(raw)
        v.require(raw == v.canonical_json(request),
                  'canonical generator invocation required')
        campaign_mode = 'campaign_context' in request
        copied.evidence._keys(request,
            'format root chunk_index recipe_id output_names external_pins '
            'source_snapshots source_revision source runtime invocation_id' +
            (' campaign_context' if campaign_mode else '') +
            (' runtime_inventory_profile_pin' if 'runtime_inventory_profile_pin' in request else ''),
            'generator invocation fields')
        v.require(request['format'] == (
                      CAMPAIGN_INVOCATION if campaign_mode else INVOCATION) and
                  request['recipe_id'] == RECIPE,
                  'invented generator invocation only')
        root = _root(request['root'])
        if campaign_mode:
            child_context.verify_context(
                request['campaign_context'], attempt_root=root,
                revision=request['source_revision'])
            v.require(request['campaign_context']['chunk_index'] ==
                      request['chunk_index'],
                      'generator campaign chunk context')
        v.require(path == root / 'owned-generator' / 'invocation.json',
                  'generator invocation path')
        operation = lambda: _generate_attempt(request, root)
        if 'runtime_inventory_profile_pin' in request:
            from . import anomaly_v03_role_runtime_observation as observation
            profile_raw = observed._file(path.parent / 'inventory-profile.json', observation.MAX_PROFILE)
            profile = observation.load_profile(profile_raw, request['runtime_inventory_profile_pin'], root=ROOT, role='producer')
            v.require(profile['source_revision'] == request['source_revision'], 'producer runtime profile worker revision differs')
            reply, receipt = observation.run_observed(operation, root=path.parent, source_root=ROOT,
                role='producer', profile_raw=profile_raw, profile_pin=request['runtime_inventory_profile_pin'],
                input_pin=copied._pin(raw))
            reply['runtime_observation'] = receipt
        else:
            reply = operation()
        print(json.dumps(reply, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        print(json.dumps({'format': FORMAT, 'status': 'failed',
                          'error_type': type(error).__name__,
                          'detail': str(error), 'formal_permission': False},
                         sort_keys=True))
        return 2


def generate_and_read(root, *, expected_pins, source_snapshots,
                      expected_revision, chunk_index=0, recipe_id=RECIPE,
                      outer_budget=None, campaign_context=None, generation_runtime_profiles=None,
                      reader_git_plan=None):
    """Own a recipe generator, verify every saved byte, then own a reader.

    ``expected_pins`` must be retained by the caller outside ``root`` before
    this function starts.  The two roles have separate engineering stop bounds;
    this wrapper does not claim a shared formal end-to-end budget.  An optional
    caller-owned engineering budget probes both child supervisors.
    """
    original_reader_git_plan = reader_git_plan
    if reader_git_plan is not None:
        reader_git_plan = copy.deepcopy(reader_git_plan)  # Before root/profile/runtime IO.
    root = _root(root)
    profiles = validate_runtime_profiles(generation_runtime_profiles, revision=expected_revision)
    if campaign_context is not None:
        campaign_context = child_context.verify_context(
            campaign_context, attempt_root=root, revision=expected_revision)
        v.require(campaign_context['chunk_index'] == chunk_index,
                  'generator campaign chunk context')
    target = root / 'owned-generator'
    active_role, active_target = 'generator', target
    result = {'format': CHAIN_FORMAT, 'status': 'failed',
              'reason': 'generator_not_completed', 'recipe_id': RECIPE,
              'invented_generation_executed': False,
              'owned_fixture_generator_executed': False,
              'owned_fixture_generator_exit_confirmed': False,
              'owned_fixture_generator_exit_reconciled': False,
              'owned_fixture_generator_pid': None,
              'owned_fixture_reader_executed': False,
              'owned_fixture_reader_exit_confirmed': False,
              'owned_fixture_reader_exit_reconciled': False,
              'owned_fixture_reader_pid': None,
              'registered_seed_consumed': False,
              'actual_registered_observations_read': False,
              'registered_observations_read': False,
              'actual_worker_exit_authenticated': False,
              'campaign_completed': False, 'campaign_evaluations_credited': 0,
              'source_closure_complete': False, 'runtime_closure_complete': False,
              'execution_authenticated': False, 'result_trusted': False,
              'formal_permission': False, 'analysis_authorized': False,
              'promotion_allowed': False, 'independent_s6_complete': False}
    if profiles is not None:
        result.update(generation_runtime_profile_pins={role: copy.deepcopy(entry['expected_pin'])
            for role, entry in profiles.items()}, generation_runtime_observation_checked=False,
            runtime_observations={}, runtime_observation_verifications={}, runtime_processes={})
    try:
        reader_git=None
        if reader_git_plan is not None:
            fields={'channel_root','policy','source_pins'}
            v.require(type(reader_git_plan) is dict and fields <= set(reader_git_plan) <= fields|{
                'pipe_raw_limits','append_control_limits'}
                and outer_budget is not None and profiles is not None,
                'reader Git requires caller plan, linked budget and fresh profiles')
            from . import anomaly_v03_preformal_reader_git_worker as reader_git_worker
            reader_names=reader_git_worker.source_names(copied.SOURCE_FILES)
            if 'pipe_raw_limits' in reader_git_plan:
                reader_git_worker._pipe_raw_limits(reader_git_plan['pipe_raw_limits'],
                    reader_git_plan['source_pins'],reader_names)
            if 'append_control_limits' in reader_git_plan:
                v.require('pipe_raw_limits' in reader_git_plan,'reader append caller requires explicit raw allocation')
                reader_git_worker.actors.archive.ArchiveAppendAdmission.validate_controls(
                    reader_git_plan['append_control_limits'])
        if outer_budget is not None:
            outer_budget.checkpoint('preflight')
        v.require(recipe_id == RECIPE, 'invented generator recipe only')
        names = _preflight(root, chunk_index, expected_pins)
        _validated_snapshots(source_snapshots, expected_revision)
        encoded_snapshots = copied._source_snapshots(source_snapshots)
        external = copy.deepcopy(expected_pins)
        target.mkdir()
        source = _source(expected_revision)
        reader_source = (copied._source(expected_revision) if reader_git_plan is None else
            reader_git_worker.selected_source(ROOT,expected_revision,reader_git_plan['source_pins'],reader_names))
        observed_runtime = runtime.probe_runtime(ROOT)
        if profiles is not None:
            check_runtime_profiles(profiles, revision=expected_revision,
                source_pins={row['path']: row['pin'] for row in source['selected_files']},
                reader_source_pins={row['path']: row['pin'] for row in reader_source['selected_files']},
                runtime=observed_runtime, **({'reader_source_names':reader_names} if reader_git_plan is not None else {}))
        if reader_git_plan is not None:
            options={} if 'pipe_raw_limits' not in reader_git_plan else {
                'pipe_raw_limits':reader_git_plan['pipe_raw_limits']}
            if 'append_control_limits' in reader_git_plan:
                options['append_control_limits']=reader_git_plan['append_control_limits']
            reader_git=reader_git_worker.ReaderGitParent.create(root=reader_git_plan['channel_root'],
                revision=expected_revision,repository=ROOT,policy=reader_git_plan['policy'],
                budget=outer_budget,source_pins=reader_git_plan['source_pins'],names=reader_names,
                profile_pin=profiles['initial-reader']['expected_pin'],**options)
        invocation = {'format': (CAMPAIGN_INVOCATION if campaign_context
                                 is not None else INVOCATION),
                      'root': str(root),
                      'chunk_index': chunk_index, 'recipe_id': RECIPE,
                      'output_names': names, 'external_pins': external,
                      'source_snapshots': encoded_snapshots,
                      'source_revision': expected_revision,
                      'source': source, 'runtime': observed_runtime,
                      'invocation_id': secrets.token_hex(32)}
        if campaign_context is not None:
            invocation['campaign_context'] = copy.deepcopy(campaign_context)
        if profiles is not None:
            invocation['runtime_inventory_profile_pin'] = copy.deepcopy(profiles['producer']['expected_pin'])
            io._exclusive(target / 'inventory-profile.json', profiles['producer']['raw'])
        invocation_raw = v.canonical_json(invocation)
        v.require(len(invocation_raw) <= MAX_INVOCATION,
                  'generator invocation byte bound')
        invocation_path = target / 'invocation.json'
        io._exclusive(invocation_path, invocation_raw)
        invocation_pin = copied._pin(invocation_raw)
        result['generator_invocation_pin'] = invocation_pin
        launch = {}

        def boundary():
            if campaign_context is not None:
                child_context.verify_context(
                    campaign_context, attempt_root=root,
                    revision=expected_revision)
            copied._same(_source(expected_revision), source,
                         'parent generator source changed')
            copied._same(runtime.probe_runtime(ROOT), observed_runtime,
                         'parent generator runtime changed')
            copied._same(copied._pin(observed._file(
                invocation_path, MAX_INVOCATION)), invocation_pin,
                'generator invocation changed')
            if profiles is not None:
                from . import anomaly_v03_role_runtime_observation as observation
                copied.pinned.read_pinned(target / 'inventory-profile.json', profiles['producer']['expected_pin'],
                                         observation.MAX_PROFILE)

        def started(process):
            launch.update(observed.creation_observation(
                process.pid, process._handle))

        if outer_budget is not None:
            outer_budget.checkpoint('generator')
        argv = [sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP,
                str(ROOT / 'src'), str(invocation_path),
                invocation_pin['sha256']]
        with platform._platform_scope():
            monitor = supervisor.supervise(
                argv, ROOT, target / 'worker', LIMITS,
                boundary=boundary, on_started=started,
                **({'resource_probe': outer_budget.probe}
                   if outer_budget is not None else {}))
        monitor_raw = v.canonical_json(monitor)
        io._exclusive(target / 'supervision.json', monitor_raw)
        if outer_budget is not None:
            outer_budget.record_role(
                'generator', monitor['status'], copied._pin(monitor_raw),
                monitor['worker_pid'], monitor['worker_exit_confirmed'])
        result.update(owned_fixture_generator_executed=monitor['worker_started'],
                      owned_fixture_generator_exit_confirmed=
                          monitor['worker_exit_confirmed'],
                      owned_fixture_generator_pid=monitor['worker_pid'],
                      owned_fixture_generator_start_token=
                          launch.get('start_token'),
                      generator_stdout_pin=monitor['output'])
        v.require(monitor['status'] == 'complete' and monitor['exit_code'] == 0
                  and monitor['worker_exit_confirmed'] is True and
                  launch.get('pid') == monitor['worker_pid'],
                  'owned generator completion required')
        stdout = observed._file(target / 'worker' / 'report.json',
                                LIMITS['output_bytes'])
        copied._same(copied._pin(stdout), monitor['output'],
                     'generator stdout pin')
        reply = v.strict_json(stdout)
        v.require(reply['format'] == (CAMPAIGN_FORMAT if campaign_context
                                     is not None else FORMAT) and
                  reply['status'] == 'generated'
                  and reply['invocation_id'] == invocation['invocation_id'] and
                  reply['process'] == {
                      'pid': launch['pid'], 'parent_pid': os.getpid(),
                      'start_token': launch['start_token']} and
                  reply['recipe_id'] == RECIPE and
                  reply['output_file_count'] == len(names) and
                  reply['output_bytes'] == sum(p['bytes'] for p in external.values())
                  and reply['invented_generation_executed'] is True and
                  reply['registered_seed_consumed'] is False and
                  reply['actual_registered_observations_read'] is False and
                  reply['formal_permission'] is False,
                  'owned generator process and fixture scope')
        if campaign_context is not None:
            copied._same(reply.get('campaign_context'), campaign_context,
                         'generator child campaign echo')
        for key, expected in (('output_pins', external),
                              ('source_before', source),
                              ('source_after', source),
                              ('runtime_before', observed_runtime),
                              ('runtime_after', observed_runtime)):
            copied._same(reply[key], expected, 'generator child ' + key)
        verification = _runtime_reply(reply, role='producer', target=target, profiles=profiles,
                                      input_pin=invocation_pin, process=launch)
        if profiles is not None:
            result['runtime_observations']['producer'] = copy.deepcopy(reply['runtime_observation'])
            result['runtime_observation_verifications']['producer'] = verification
            result['runtime_processes']['producer'] = copy.deepcopy(launch)
            if outer_budget is not None:
                outer_budget.checkpoint('generator')
        copied._check_outputs(root, names, external)
        boundary()
        selected, attempt = copied._saved_outputs(
            root, chunk_index, external)
        copied._same(selected, names, 'generated reader output names')
        result.update(invented_generation_executed=True,
                      generated_file_count=len(names),
                      generated_output_pins=external)

        active_role = 'reader'
        active_target = root / 'owned-reader'
        if outer_budget is not None:
            outer_budget.checkpoint('reader')
        active_target.mkdir()
        reader_invocation = {
            'format': (copied.CAMPAIGN_READER_INVOCATION if campaign_context
                       is not None else copied.READER_INVOCATION),
            'root': str(root),
            'expected_mode': saved.MODE, 'chunk_index': chunk_index,
            'output_names': names, 'external_pins': external,
            'source_snapshots': encoded_snapshots,
            'source_revision': expected_revision, 'source': reader_source,
            'runtime': observed_runtime,
            'invocation_id': secrets.token_hex(32)}
        if campaign_context is not None:
            reader_invocation['campaign_context'] = copy.deepcopy(
                campaign_context)
        if profiles is not None:
            reader_invocation['runtime_inventory_profile_pin'] = copy.deepcopy(profiles['initial-reader']['expected_pin'])
            io._exclusive(active_target / 'inventory-profile.json', profiles['initial-reader']['raw'])
        if reader_git is not None:
            copied._same(reader_git.profile_pin,profiles['initial-reader']['expected_pin'],
                         'reader caller-held runtime profile pin')
            reader_invocation['worker_git_entry']=copy.deepcopy(reader_git.entry)
        reader_raw = v.canonical_json(reader_invocation)
        v.require(len(reader_raw) <= copied.MAX_READER_INVOCATION,
                  'reader invocation byte bound')
        reader_path = active_target / 'invocation.json'
        io._exclusive(reader_path, reader_raw)
        reader_pin = copied._pin(reader_raw)
        result['reader_invocation_pin'] = reader_pin
        reader_launch = {}

        def reader_boundary():
            boundary()
            copied._same(copied._source(expected_revision) if reader_git is None else reader_git.source(), reader_source,
                         'parent reader source changed')
            copied._check_outputs(root, names, external)
            copied._same(copied._pin(observed._file(
                reader_path, copied.MAX_READER_INVOCATION)), reader_pin,
                'reader invocation changed')
            if profiles is not None:
                from . import anomaly_v03_role_runtime_observation as observation
                copied.pinned.read_pinned(active_target / 'inventory-profile.json', profiles['initial-reader']['expected_pin'],
                                         observation.MAX_PROFILE)

        def reader_started(process):
            reader_launch.update(observed.creation_observation(process.pid,process._handle)
                if reader_git is None else reader_git.bind(process))

        reader_argv = [sys.executable, '-I', '-S', '-B', '-c',
                       copied.READER_BOOTSTRAP, str(ROOT / 'src'),
                       str(reader_path), reader_pin['sha256']]
        with platform._platform_scope():
            reader_monitor = supervisor.supervise(
                reader_argv, ROOT, active_target / 'worker',
                copied.READER_LIMITS, boundary=reader_boundary,
                on_started=reader_started,
                **({'stop_fence':reader_git.fence} if reader_git is not None else {}),
                **({'resource_probe': outer_budget.probe}
                   if outer_budget is not None else {}))
        reader_monitor_raw = v.canonical_json(reader_monitor)
        io._exclusive(active_target / 'supervision.json', reader_monitor_raw)
        if outer_budget is not None:
            outer_budget.record_role(
                'reader', reader_monitor['status'],
                copied._pin(reader_monitor_raw),
                reader_monitor['worker_pid'],
                reader_monitor['worker_exit_confirmed'])
        result.update(owned_fixture_reader_executed=
                          reader_monitor['worker_started'],
                      owned_fixture_reader_exit_confirmed=
                          reader_monitor['worker_exit_confirmed'],
                      owned_fixture_reader_pid=reader_monitor['worker_pid'],
                      owned_fixture_reader_start_token=
                          reader_launch.get('start_token'),
                      reader_stdout_pin=reader_monitor['output'])
        v.require(reader_monitor['status'] == 'complete' and
                  reader_monitor['exit_code'] == 0 and
                  reader_monitor['worker_exit_confirmed'] is True and
                  reader_launch.get('pid') == reader_monitor['worker_pid'],
                  'owned reader completion required')
        reader_stdout = observed._file(
            active_target / 'worker' / 'report.json',
            copied.READER_LIMITS['output_bytes'])
        copied._same(copied._pin(reader_stdout), reader_monitor['output'],
                     'reader stdout pin')
        reader_reply = v.strict_json(reader_stdout)
        v.require(reader_reply['format'] == (
                      copied.CAMPAIGN_READER_FORMAT if campaign_context
                      is not None else copied.READER_FORMAT) and
                  reader_reply['status'] == 'read' and
                  reader_reply['invocation_id'] ==
                      reader_invocation['invocation_id'] and
                  reader_reply['process'] == {
                      'pid': reader_launch['pid'], 'parent_pid': os.getpid(),
                      'start_token': reader_launch['start_token']} and
                  reader_reply['formal_permission'] is False,
                  'owned reader process binding')
        if campaign_context is not None:
            copied._same(reader_reply.get('campaign_context'),
                         campaign_context, 'initial reader campaign echo')
        for key, expected in (('output_pins', external),
                              ('source_before', reader_source),
                              ('source_after', reader_source),
                              ('runtime_before', observed_runtime),
                              ('runtime_after', observed_runtime)):
            copied._same(reader_reply[key], expected, 'reader child ' + key)
        verification = _runtime_reply(reader_reply, role='initial-reader', target=active_target,
                                      profiles=profiles, input_pin=reader_pin, process=reader_launch)
        if profiles is not None:
            result['runtime_observations']['initial-reader'] = copy.deepcopy(reader_reply['runtime_observation'])
            result['runtime_observation_verifications']['initial-reader'] = verification
            result['runtime_processes']['initial-reader'] = copy.deepcopy(reader_launch)
        read = reader_reply['reader_result']
        for key, expected in {
            'format': fixture.FORMAT,
            'status': 'latest_chunk_saved_bytes_bound',
            'mode': saved.MODE, 'chunk_index': chunk_index,
            'latest_state': 'complete', 'latest_attempt': attempt,
            'latest_rows_bound': 6,
            'scope': 'invented-registered-format-actual-attempt-layout-only',
            'fixture_physical_layout': 'run-attempt-result-payload',
            'fixture_saved_files_read': True,
            'fixture_files_read': len(names),
            'registered_evaluation_contracts_checked': 6,
            'saved_payload_bytes_verified': True,
            'external_report_bytes_verified': True,
            'reported_score_ledger_recomputed': True,
            'reported_score_to_primary_summary_checked': True,
            'reported_score_to_slice_summary_recomputed': True,
            'receipt_pin': external['saved/receipt.json'],
            'report_pin': external['saved/report.json'],
            'payload_pins': {key: value for key, value in external.items()
                             if key not in copied.SAVED},
            'invented_registered_format_observations_read': True,
            'invented_observation_profile_score_recomputed': True,
            'observation_to_profile_recomputed': True,
            'observation_to_score_recomputed': True,
            'observation_to_summary_recomputed': True,
            'source_savepoint_bytes_verified': True,
            'source_snapshots_caller_supplied': True,
            'actual_registered_observations_read': False,
            'registered_observations_read': False,
            'real_saved_chunk_reader_used': False,
            'reader_result_provenance_authenticated': False,
            'registered_input_bytes_verified': False,
            'actual_worker_exit_authenticated': False,
            'campaign_completed': False,
            'campaign_evaluations_credited': 0,
            'source_closure_complete': False,
            'runtime_closure_complete': False,
            'execution_authenticated': False,
            'result_trusted': False,
            'formal_permission': False,
            'analysis_authorized': False,
            'promotion_allowed': False,
            'independent_s6_complete': False,
        }.items():
            copied._same(read[key], expected, 'owned reader result ' + key)
        reader_boundary()
        recheck_runtime_profiles(root, result)
        if outer_budget is not None:
            outer_budget.checkpoint('postflight')
        if profiles is not None:
            result['generation_runtime_observation_checked'] = True
        result.update(status='verified', reason=None, reader_result=read)
    except supervisor.UnreapedWorker as error:
        report = error.report
        field = 'owned_fixture_' + active_role
        result.update(reason='unreaped_' + active_role + '_failure',
                      failed_stage=active_role)
        result[field + '_executed'] = report.get('worker_started', False)
        result[field + '_pid'] = report.get('worker_pid')
        result[field + '_exit_confirmed'] = False
        result[field + '_exit_reconciled'] = False
        try:
            supervisor.retain_until_exit(error)
        except BaseException:
            try:
                io._exclusive(active_target / 'supervision.json',
                              v.canonical_json(report))
                io._exclusive(target / 'result.json', v.canonical_json(result))
            except BaseException:
                pass
            raise error
        io._exclusive(active_target / 'supervision.json',
                      v.canonical_json(report))
        result.update(reason='unreaped_' + active_role + '_reconciled_failure')
        result[field + '_exit_reconciled'] = True
    except resources.ResourceStop as error:
        result.update(reason=error.reason, failed_stage=active_role,
                      error_type=type(error).__name__)
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        result.update(reason='generator_or_reader_rejected',
                      failed_stage=active_role,
                      error_type=type(error).__name__, detail=str(error))
    if not target.exists():
        target.mkdir()
    io._exclusive(target / 'result.json', v.canonical_json(result))
    return {**result, 'check_directory': str(target),
            'result_pin': copied._pin(v.canonical_json(result))}
