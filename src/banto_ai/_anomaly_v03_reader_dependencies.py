"""Bounded snapshots of reader imports and loaded Windows images.

This module deliberately does not import site or the producer inventory tool.
Disk bytes are observations, not proof of in-memory code or a complete closure.
Existing bytecode cache candidates are recorded without claiming they were used.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import hashlib
import importlib.machinery
import os
from pathlib import Path
import stat
import sys

from . import anomaly_v03 as v
from . import _anomaly_v03_runtime as rt

FORMAT = 'anomaly-v03-reader-dependencies-v1'
MAX_FILES = 512
MAX_FILE = 64 * 1024**2
MAX_TOTAL = 256 * 1024**2
SCOPE = {'source_closure_complete': False, 'runtime_closure_complete': False,
         'execution_authenticated': False, 'formal_permission': False,
         'cache_policy': 'existing-candidates-not-proven-loaded',
         'file_policy': 'disk-bytes-not-in-memory-code',
         'native_policy': 'python-system32-or-exact-parent-loaded-external-image'}
PROFILE_FORMAT = 'anomaly-v03-reader-dependency-profile-v1'
PROFILE_MAX = 512 * 1024
PROFILE_BOUNDARY = 'request-decoded-collector-imported-before-publication-read-v1'
FIVE_ROLE_PROFILE_FORMAT = 'anomaly-v03-preformal-five-role-dependency-profile-v3'
FIVE_ROLE_OPERATIONS = {
    'producer': 'join-invented-archive-and-project-one-draw',
    'analysis': 'assemble-invented-document-v1',
    'audit': 'audit-invented-primary-and-slices-v1',
    'writer': 'publish-invented-five-payloads',
    'reader': 'readback-invented-five-payloads',
}
FIVE_ROLE_BOUNDARIES = {
    'producer': 'invocation-decoded-before-invented-archive-read-v1',
    'analysis': 'request-loaded-before-invented-document-assembly-v1',
    'audit': 'request-loaded-before-independent-invented-audit-v1',
    'writer': 'publication-inputs-loaded-before-publish-v1',
    'reader': 'publication-inputs-loaded-before-readback-v1',
}


def load_profile(raw, expected_pin, *, root, revision):
    """Decode a caller-pinned engineering candidate without opening its paths."""
    from . import anomaly_v03_consumer_evidence as evidence
    v.require(type(raw) is bytes and 0 < len(raw) <= PROFILE_MAX, 'dependency profile size')
    evidence._raw(raw, expected_pin, 'retained dependency profile pin')
    profile = v.strict_json(raw)
    evidence._keys(profile, 'format mode role acceptance source_revision root runtime snapshot boundary reference scope',
                   'dependency profile fields')
    v.require(profile['format'] == PROFILE_FORMAT and profile['mode'] == 'engineering-dev-smoke'
              and profile['role'] == 'reader' and profile['acceptance'] == 'candidate-not-accepted',
              'dependency profile role/mode/acceptance')
    evidence._digest(revision, 40)
    v.require(profile['source_revision'] == revision and profile['root'] == str(root), 'dependency profile source/root')
    v.require(profile['boundary'] == PROFILE_BOUNDARY and profile['scope'] == SCOPE, 'dependency profile scope/boundary')
    evidence._runtime(profile['runtime'])
    evidence._keys(profile['reference'], 'result_pin evidence_pin dependency_pin stdout_pin', 'dependency profile reference')
    for pin in profile['reference'].values(): evidence._pin(pin)
    snapshot = profile['snapshot']
    evidence._keys(snapshot, 'format modules files native_files scope', 'dependency profile snapshot')
    v.require(snapshot['format'] == FORMAT and snapshot['scope'] == SCOPE, 'dependency profile snapshot scope')
    v.require(type(snapshot['files']) is dict and 0 < len(snapshot['files']) <= MAX_FILES, 'dependency profile files')
    v.require(type(snapshot['modules']) is dict and len(snapshot['modules']) <= 2048, 'dependency profile modules')
    return profile


def match_profile(profile, snapshot, runtime, *, phase):
    """Exact comparison against pre-retained bytes, including extra imports."""
    v.require(phase in ('before', 'after'), 'dependency profile comparison phase')
    v.require(runtime == profile['runtime'], 'dependency profile runtime '+phase+' mismatch')
    v.require(snapshot == profile['snapshot'], 'dependency profile inventory '+phase+' mismatch')


def load_five_role_profile(raw, expected_pin, *, role, root, revision):
    """Load a caller-pinned, invented-only role candidate without trusting its path."""
    from . import anomaly_v03_consumer_evidence as evidence
    v.require(role in FIVE_ROLE_OPERATIONS and type(raw) is bytes and
              0 < len(raw) <= PROFILE_MAX, 'five-role profile size/role')
    evidence._raw(raw, expected_pin, 'retained five-role profile pin')
    profile = v.strict_json(raw)
    evidence._keys(profile, 'format mode role operation boundary acceptance '
                   'source_revision root runtime snapshots observation_semantics '
                   'crosscheck_scope reference_root reference scope formal_permission '
                   'source_closure_complete runtime_closure_complete',
                   'five-role profile fields')
    v.require(profile['format'] == FIVE_ROLE_PROFILE_FORMAT and
              profile['mode'] == 'fixture' and profile['role'] == role and
              profile['operation'] == FIVE_ROLE_OPERATIONS[role] and
              profile['boundary'] == FIVE_ROLE_BOUNDARIES[role] and
              profile['acceptance'] == 'candidate-not-accepted' and
              profile['source_revision'] == revision and profile['root'] == str(root) and
              profile['scope'] == SCOPE and profile['formal_permission'] is False and
              profile['source_closure_complete'] is False and
              profile['runtime_closure_complete'] is False and
              profile['observation_semantics'] ==
                  'two-point-before-and-after-with-additions-only' and
              profile['crosscheck_scope'] ==
                  'historical-parent-verdict-pinned-no-current-image-allowlist',
              'five-role profile identity/scope')
    evidence._keys(profile['snapshots'], 'before after', 'five-role snapshots')
    for phase in ('before', 'after'):
        snapshot = profile['snapshots'][phase]
        evidence._keys(snapshot, 'format modules files native_files scope',
                       'five-role ' + phase + ' snapshot')
        v.require(snapshot['format'] == FORMAT and snapshot['scope'] == SCOPE and
                  type(snapshot['files']) is dict and 0 < len(snapshot['files']) <= MAX_FILES and
                  type(snapshot['modules']) is dict and len(snapshot['modules']) <= 2048 and
                  type(snapshot['native_files']) is list and
                  snapshot['native_files'] == sorted(set(snapshot['native_files'])),
                  'five-role ' + phase + ' snapshot bounds')
    for section in ('files', 'modules'):
        v.require(all(profile['snapshots']['after'][section].get(name) == row
                      for name, row in profile['snapshots']['before'][section].items()),
                  'five-role existing dependency changed/disappeared')
    v.require(set(profile['snapshots']['before']['native_files']) <=
              set(profile['snapshots']['after']['native_files']),
              'five-role native image disappeared')
    evidence._keys(profile['reference'],
                   'top_result_pin result_pin supervision_pin stdout_pin '
                   'dependency_pin crosscheck_pin' +
                   ('' if role == 'producer' else ' evidence_pin'),
                   'five-role reference pins')
    for pin in profile['reference'].values():
        evidence._pin(pin)
    return profile


def match_five_role_profile(profile, snapshot, runtime, *, phase):
    """Exact role observation comparison; a late addition is only allowed after work."""
    v.require(phase in ('before', 'after'), 'five-role profile phase')
    v.require(runtime == profile['runtime'], 'five-role profile runtime ' + phase + ' mismatch')
    v.require(snapshot == profile['snapshots'][phase],
              'five-role profile inventory ' + phase + ' mismatch')


def _stamp(meta):
    v.require(stat.S_ISREG(meta.st_mode) and meta.st_ino != 0 and meta.st_nlink >= 1,
              'dependency is not a regular identified file')
    return {'device': meta.st_dev, 'inode': meta.st_ino, 'links': meta.st_nlink,
            'bytes': meta.st_size, 'mtime_ns': meta.st_mtime_ns}


def file_observation(path, *, native=False, maximum=MAX_FILE):
    """Hash with a bounded buffer, retaining the same file identity throughout."""
    path = Path(path)
    before = _stamp(path.lstat())
    v.require(native or before['links'] == 1, 'dependency source/cache hardlink')
    rt.regular_path(path, links=before['links'])
    v.require(before['bytes'] <= maximum, 'dependency file limit')
    digest, count = hashlib.sha256(), 0
    with path.open('rb') as stream:
        v.require(_stamp(os.fstat(stream.fileno())) == before, 'dependency changed on open')
        while block := stream.read(min(1024**2, maximum + 1 - count)):
            count += len(block)
            v.require(count <= maximum, 'dependency grew over limit')
            digest.update(block)
        v.require(_stamp(os.fstat(stream.fileno())) == before, 'dependency changed during hash')
    rt.regular_path(path, links=before['links'])
    v.require(_stamp(path.lstat()) == before and count == before['bytes'], 'dependency changed after hash')
    return {'physical_path': str(path), 'pin': {'bytes': count, 'sha256': digest.hexdigest()},
            'identity': before}


def windows_modules():
    v.require(os.name == 'nt', 'Windows dependency observation required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    psapi.EnumProcessModulesEx.argtypes = [w.HANDLE, ctypes.POINTER(w.HMODULE), w.DWORD,
                                          ctypes.POINTER(w.DWORD), w.DWORD]
    psapi.EnumProcessModulesEx.restype = w.BOOL
    kernel.GetModuleFileNameW.argtypes = [w.HMODULE, w.LPWSTR, w.DWORD]
    kernel.GetModuleFileNameW.restype = w.DWORD
    modules, needed = (w.HMODULE * MAX_FILES)(), w.DWORD()
    v.require(psapi.EnumProcessModulesEx(kernel.GetCurrentProcess(), modules, ctypes.sizeof(modules),
              ctypes.byref(needed), 3), 'loaded image enumeration failed')
    v.require(0 < needed.value <= ctypes.sizeof(modules) and needed.value % ctypes.sizeof(w.HMODULE) == 0,
              'loaded image enumeration limit')
    paths = []
    for handle in modules[:needed.value // ctypes.sizeof(w.HMODULE)]:
        name = ctypes.create_unicode_buffer(32768)
        length = kernel.GetModuleFileNameW(handle, name, len(name))
        v.require(0 < length < len(name), 'loaded image path unavailable')
        paths.append(Path(name.value))
    return sorted(set(paths), key=lambda p: str(p).casefold())


def system32():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes = [w.LPWSTR, w.UINT]
    kernel.GetSystemDirectoryW.restype = w.UINT
    name = ctypes.create_unicode_buffer(32768)
    count = kernel.GetSystemDirectoryW(name, len(name))
    v.require(0 < count < len(name), 'Windows system directory unavailable')
    return Path(name.value)


def _location(path, root, base, windows, *, native=False, external_images=()):
    """Validate before opening any path supplied by a child observation."""
    path = Path(path)
    v.require(path.is_absolute() and '..' not in path.parts and ':' not in str(path)[2:], 'dependency absolute path')
    if path.is_relative_to(root / 'src'):
        v.require(not native, 'native image in project source')
        return 'project/' + path.relative_to(root).as_posix(), 'project'
    if path.is_relative_to(base):
        relative = path.relative_to(base)
        v.require('site-packages' not in [p.casefold() for p in relative.parts], 'third-party dependency')
        return 'python-files/' + relative.as_posix(), 'native' if native else 'stdlib'
    if native and path.is_relative_to(windows):
        return 'windows-system32/' + path.relative_to(windows).as_posix(), 'native'
    v.require(native and path in external_images, 'dependency outside permitted observation roots')
    return 'external-native/' + path.name, 'native'


def _inventory(root):
    base, windows = Path(sys.base_prefix), system32()
    # Load enumeration libraries before taking the module list.
    images = windows_modules()
    files, physical, modules = {}, {}, {}

    def add(path, *, native=False, cache=False):
        path = Path(path)
        logical, category = _location(path, root, base, windows, native=native, external_images=images)
        key = str(path).casefold()
        if key in physical:
            return physical[key]
        if cache:
            try: path.lstat()
            except FileNotFoundError: return None
            category = 'bytecode-cache-candidate'
        if native and any(str(path).lower().endswith(s.lower()) for s in importlib.machinery.EXTENSION_SUFFIXES):
            category = 'extension'
        v.require(logical.casefold() not in {n.casefold() for n in files}, 'dependency logical alias')
        v.require(len(files) < MAX_FILES, 'dependency inventory limit')
        physical[key] = logical
        files[logical] = {'physical_path': str(path), 'category': category, 'native': native}
        return logical

    native_names = [add(path, native=True) for path in images]
    for name, module in sorted(tuple(sys.modules.items())):
        spec = getattr(module, '__spec__', None)
        origin = getattr(spec, 'origin', None)
        row = {'kind': origin if origin in ('built-in', 'frozen') else 'no-file', 'file': None, 'cache_candidate': None}
        if origin and origin not in ('built-in', 'frozen'):
            extension = any(origin.lower().endswith(s.lower()) for s in importlib.machinery.EXTENSION_SUFFIXES)
            row['kind'] = 'extension' if extension else 'file'
            if extension:
                v.require(Path(origin) in images, 'Python extension missing from loaded images')
            row['file'] = add(origin, native=extension)
            cached = getattr(spec, 'cached', None)
            if cached and cached != origin:
                row['cache_candidate'] = add(cached, cache=True)
        modules[name] = row
    return {'modules': modules, 'files': files, 'native_files': sorted(native_names)}


def collect(root):
    """Snapshot after collector imports; import origins and loaded images only."""
    root = Path(root)
    inventory = _inventory(root)
    rows, total = {}, 0
    for name, row in sorted(inventory['files'].items()):
        observed = file_observation(row['physical_path'], native=row['native'], maximum=min(MAX_FILE, MAX_TOTAL-total))
        total += observed['pin']['bytes']
        rows[name] = {**observed, 'category': row['category'], 'native': row['native']}
    v.require(inventory == _inventory(root), 'imports/images changed during dependency snapshot')
    return {'format': FORMAT, 'modules': inventory['modules'], 'files': rows,
            'native_files': inventory['native_files'], 'scope': dict(SCOPE)}


def verify_pair(before, after, *, root, revision, git, required_sources):
    """Parent post-exit disk/Git crosscheck, NOT independent runtime preflight.

    The child supplies the inventory. New imports may appear during the read;
    existing rows may not disappear or change. No completeness claim is made.
    """
    root, base, windows = Path(root), Path(sys.base_prefix), system32()
    parent_images = windows_modules()
    for snapshot in (before, after):
        v.require(type(snapshot) is dict and set(snapshot) == {'format','modules','files','native_files','scope'}, 'dependency snapshot fields')
        v.require(snapshot['format'] == FORMAT and snapshot['scope'] == SCOPE, 'dependency observation scope')
        rows = snapshot['files']
        v.require(type(rows) is dict and 1 <= len(rows) <= MAX_FILES, 'dependency snapshot file limit')
        v.require(type(snapshot['modules']) is dict and len(snapshot['modules']) <= 2048, 'dependency module limit')
        v.require(type(snapshot['native_files']) is list and snapshot['native_files'] == sorted(set(snapshot['native_files'])), 'dependency native inventory')
        physical, total = set(), 0
        for name, row in rows.items():
            v.require(type(row) is dict and set(row) == {'physical_path','pin','identity','category','native'}, 'dependency file fields')
            v.require(type(row['native']) is bool, 'dependency native flag')
            path = Path(row['physical_path'])
            logical, category = _location(path, root, base, windows, native=row['native'], external_images=parent_images)
            if row['native'] and any(str(path).lower().endswith(s.lower()) for s in importlib.machinery.EXTENSION_SUFFIXES): category = 'extension'
            if row['category'] == 'bytecode-cache-candidate':
                v.require(not row['native'] and path.suffix == '.pyc', 'dependency cache candidate')
                category = row['category']
            v.require(name == logical and row['category'] == category, 'dependency logical/category mismatch')
            key = str(path).casefold()
            v.require(key not in physical, 'dependency physical alias'); physical.add(key)
            observed = file_observation(path, native=row['native'], maximum=min(MAX_FILE, MAX_TOTAL-total))
            total += observed['pin']['bytes']
            v.require(row == {**observed, 'category': category, 'native': row['native']}, 'parent dependency disk mismatch')
            v.require((name in snapshot['native_files']) == row['native'], 'dependency native reference')
            if category == 'project':
                relative = path.relative_to(root).as_posix()
                raw = git('show', revision+':'+relative)
                v.require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == row['pin'], 'dependency working/Git bytes differ: '+relative)
        v.require(set(snapshot['native_files']) <= set(rows), 'unknown native dependency')
        for name, row in snapshot['modules'].items():
            v.require(type(name) is str and type(row) is dict and set(row) == {'kind','file','cache_candidate'}, 'dependency module fields')
            v.require(row['kind'] in ('built-in','frozen','no-file','file','extension'), 'dependency module kind')
            v.require((row['file'] is not None) == (row['kind'] in ('file','extension')), 'dependency module file')
            for field in ('file','cache_candidate'):
                v.require(row[field] is None or row[field] in rows, 'missing module file reference')
            if row['kind'] == 'extension': v.require(row['file'] in snapshot['native_files'], 'extension/native reference')
            if row['cache_candidate'] is not None:
                v.require(rows[row['cache_candidate']]['category'] == 'bytecode-cache-candidate', 'cache candidate reference')
        v.require({'project/'+n for n in required_sources} <= set(rows), 'required reader dependency missing')
    for section in ('files', 'modules'):
        v.require(all(after[section].get(n) == row for n, row in before[section].items()), 'reader dependency changed/disappeared')
    source_count = sum(r['category'] == 'project' for r in after['files'].values())
    return {'status': 'observed_dependencies_disk_git_matched', **SCOPE,
            'expectation_origin': 'child-inventory-crosschecked-by-parent-after-exit',
            'project_files': source_count, 'files': len(after['files']), 'modules': len(after['modules']),
            'native_files': len(after['native_files']),
            'added_files_during_read': sorted(set(after['files'])-set(before['files'])),
            'added_modules_during_read': sorted(set(after['modules'])-set(before['modules']))}


# These engineering candidates use a new operation and versions. They are not
# issued worker requests, native receipts, or extensions to the existing v1 proof.
SOURCE_BATCH_REQUEST = 'anomaly-v03-source-batch-request-candidate-v1'
SOURCE_BATCH_PROOF = 'anomaly-v03-source-batch-proof-candidate-v1'
SOURCE_BATCH_TRANSPORT = 'anomaly-v03-source-batch-packed-raw-candidate-v1'
SOURCE_BATCH_SCOPE = {'source_closure_complete': False, 'runtime_closure_complete': False,
                      'execution_authenticated': False, 'formal_permission': False,
                      'native_authorized': False, 'capacity_pass': False}
BATCH_STDOUT_MAX = 131072
BATCH_MEMBERS_MAX = 16
BATCH_CALLS_MAX = 64
BATCH_PACK_MAX = 524288


def _batch_scope():
    return {key: False for key in ('source_closure_complete', 'runtime_closure_complete',
        'execution_authenticated', 'formal_permission', 'native_authorized', 'capacity_pass')}


def _batch_json(value):
    return v.json.dumps(value, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=True, allow_nan=False).encode('ascii')


def _batch_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _batch_keys(value, names, reason):
    v.require(type(value) is dict and set(value) == set(names.split()), reason)


def _batch_digest(value, width):
    v.require(type(value) is str and len(value) == width and
              all(c in '0123456789abcdef' for c in value), 'batch digest')


def _batch_sources(sources):
    v.require(type(sources) in (list, tuple) and 0 < len(sources) <= 128, 'batch source count')
    names = set()
    for row in sources:
        _batch_keys(row, 'name pin git_blob_oid', 'batch source fields')
        name = row['name']
        v.require(type(name) is str and name.startswith('src/banto_ai/') and name.endswith('.py')
                  and all(part and part not in ('.', '..') and
                          all(c.isascii() and (c.isalnum() or c in '_.-') for c in part)
                          for part in name.split('/')) and name not in names,
                  'batch unique unambiguous project source')
        names.add(name)
        _batch_keys(row['pin'], 'bytes sha256', 'batch source pin')
        _batch_digest(row['pin']['sha256'], 64); _batch_digest(row['git_blob_oid'], 40)
        size = row['pin']['bytes']
        v.require(type(size) is int and 0 <= size <= BATCH_STDOUT_MAX and
                  size + 48 + len(str(size)) <= BATCH_STDOUT_MAX, 'batch source with header byte bound')


def source_batch_request_candidate(*, revision, root, sources):
    """Compile declared source membership; no path, Git, clock or native reads."""
    _batch_digest(revision, 40)
    v.require(type(root) is str and 0 < len(root) <= 4096, 'batch declared root')
    _batch_sources(sources)
    # Copy through bounded canonical bytes so later caller mutation cannot alter
    # the generated declaration. Original references belong to the preparation.
    source_raw = _batch_json(list(sources))
    v.require(len(source_raw) <= 32768, 'batch declared source byte bound')
    frozen = v.strict_json(source_raw)
    groups = []; group = []; width = 0
    for index, row in enumerate(frozen):
        amount = row['pin']['bytes'] + 48 + len(str(row['pin']['bytes']))
        if group and (len(group) == BATCH_MEMBERS_MAX or width + amount > BATCH_STDOUT_MAX):
            groups.append({'members': group, 'stdout_bytes': width}); group = []; width = 0
        group.append(index); width += amount
    groups.append({'members': group, 'stdout_bytes': width})
    calls = []
    for phase in ('pre', 'post'):
        for operation in ('head', 'status'):
            calls.append({'phase': phase, 'operation': operation, 'group': None, 'stdout_bytes': None})
        for index, group in enumerate(groups):
            calls.append({'phase': phase, 'operation': 'source_blob_batch', 'group': index,
                          'stdout_bytes': group['stdout_bytes']})
    v.require(len(calls) <= BATCH_CALLS_MAX, 'batch lease byte-independent call bound')
    raw = _batch_json({'format': SOURCE_BATCH_REQUEST, 'revision': revision, 'root': root,
                      'object_format': 'sha1', 'sources': frozen, 'groups': groups, 'calls': calls,
                      'scope': _batch_scope()})
    v.require(len(raw) <= 32768, 'batch request candidate byte bound')
    return raw


class SourceBatchContractPreparation:
    """Same-owner memory candidates with full future raw/failure accounting.

    Packing reduces file entry arithmetic. Literal raw bytes and original partial
    bytes remain separate from future archive growth; no compression is assumed.
    This class does not issue operations or publish/recover any native resource.
    """
    def _retain_inputs(self, *, owner, checkpoint, request_raw, expected_sources, raw_maxima,
                       storage_maxima):
        incoming = (owner, checkpoint, request_raw, expected_sources, raw_maxima, storage_maxima)
        if hasattr(self, '_SourceBatchContractPreparation__inputs'):
            self.rejected_inputs = incoming
            self._failed(ValueError('batch original preparation cannot be replaced'))
        self.__inputs = incoming
        self.original_inputs = incoming
        self.owner, self.checkpoint = owner, checkpoint
        self.__error = self.error = None
        self.__records = (); self.records = ()
        self.__record_bindings = ()
        self.__pending = self.pending = None
        self.__packing = False
        self.__pack = None
        self.__pack_anchor = None
        self.__proof_raw = None
        self.__initialized = False

    def __init__(self, *, owner, checkpoint, request_raw, expected_sources, raw_maxima, storage_maxima):
        if not hasattr(self, '_SourceBatchContractPreparation__inputs'):
            self._retain_inputs(owner=owner, checkpoint=checkpoint, request_raw=request_raw,
                                expected_sources=expected_sources, raw_maxima=raw_maxima,
                                storage_maxima=storage_maxima)
        if self.__initialized:self._failed(ValueError('batch original preparation initializes once'))
        self.__initialized = True
        try:
            v.require(all(a is b for a, b in zip(self.__inputs,
                (owner, checkpoint, request_raw, expected_sources, raw_maxima, storage_maxima))),
                'batch original inputs')
            v.require(type(request_raw) is bytes and 0 < len(request_raw) <= 32768,
                      'batch request raw bound')
            request = self.__request = v.strict_json(request_raw)
            _batch_keys(request, 'format revision root object_format sources groups calls scope',
                        'batch closed request fields')
            v.require(request['format'] == SOURCE_BATCH_REQUEST and request['object_format'] == 'sha1'
                      and request['scope'] == _batch_scope(), 'batch candidate format/scope')
            _batch_sources(expected_sources)
            v.require(request['sources'] == list(expected_sources), 'batch independent exact source coverage')
            v.require(source_batch_request_candidate(revision=request['revision'], root=request['root'],
                sources=expected_sources) == request_raw, 'batch canonical complete ordered plan')
            self.__request_raw = request_raw
            v.require(type(raw_maxima) in (list, tuple) and len(raw_maxima) == len(request['calls']),
                      'batch all planned raw maxima')
            self.__maxima_raw = _batch_json(list(raw_maxima))
            self.__maxima = v.strict_json(self.__maxima_raw)
            maximum = 8 + 20 * len(raw_maxima)
            for call, limits in zip(request['calls'], self.__maxima):
                _batch_keys(limits, 'stdout stderr receipt partial', 'batch per-call failure maxima')
                for name, cap in (('stdout',131072), ('stderr',16384), ('receipt',32768), ('partial',131072)):
                    v.require(type(limits[name]) is int and 0 <= limits[name] <= cap, 'batch raw maximum bound')
                v.require(limits['receipt'] > 0 and (call['stdout_bytes'] is None or
                    limits['stdout'] >= call['stdout_bytes']), 'batch success and failure raw maxima')
                maximum += sum(limits.values())  # Includes every planned call, even completed calls.
            self.maximum_packed_raw_bytes = maximum
            self.__storage_raw = _batch_json(storage_maxima)
            _batch_keys(storage_maxima, 'control parent_failure diagnostic entry_context_identity '
                        'carrier_failure archive_new_growth partial_raw reserve snapshot', 'batch storage maxima')
            entries = {'control':14,'parent_failure':3,'diagnostic':2,'entry_context_identity':3,
                       'carrier_failure':2,'archive_new_growth':1,'partial_raw':1,'reserve':2}
            total_entries = 1; total_bytes = maximum  # One future literal call raw pack.
            for name, row in storage_maxima.items():
                _batch_keys(row, 'bytes entries', 'batch storage row')
                v.require(type(row['bytes']) is int and row['bytes'] >= 0 and
                          type(row['entries']) is int and row['entries'] >= 0, 'batch storage amounts')
                v.require(row['entries'] == entries[name] if name != 'snapshot' else row['entries'] <= 32,
                          'batch no completed entry discount')
                if name == 'reserve':
                    v.require(row['bytes'] == 131072, 'batch fixed reserve bytes')
                if name == 'archive_new_growth':
                    v.require(row['bytes'] <= 524288, 'batch independent archive growth cap')
                total_entries += row['entries']; total_bytes += row['bytes']
            self.projection = {'entries':total_entries,'bytes':total_bytes,
                               'packed_raw_bytes':maximum,'scope':_batch_scope()}
            v.require(maximum <= BATCH_PACK_MAX, 'batch packed future raw byte bound')
            v.require(total_entries <= 32 and total_bytes <= 1048576, 'batch full future storage bound')
        except BaseException as error:self._failed(error)

    def _failed(self, error):
        if self.__error is None:self.__error = error
        self.error = self.__error
        self.__error.source_batch_preparation = self
        self.__error.reader_git_parent = self.__inputs[0]
        raise self.__error

    def _fixed(self):
        if self.__error is not None:raise self.__error
        try:
            v.require(self.original_inputs is self.__inputs and self.owner is self.__inputs[0] and
                      self.checkpoint is self.__inputs[1] and
                      self.__inputs[2] == self.__request_raw and
                      _batch_json(self.__request) == self.__request_raw and
                      _batch_json(list(self.__inputs[3])) == _batch_json(self.__request['sources']) and
                      _batch_json(list(self.__inputs[4])) == self.__maxima_raw and
                      _batch_json(self.__inputs[5]) == self.__storage_raw and
                      self.records is self.__records and self.pending is self.__pending,
                      'batch original private input/return bindings')
            for held, incoming, proof_raw in self.__record_bindings:
                v.require(held['incoming'] is incoming and held['proof_raw'] is proof_raw and
                          held['error'] is None and held['native_authorized'] is False and
                          held['formal_permission'] is False, 'batch original private raw/proof bindings')
        except BaseException as error:self._failed(error)

    def unresolved(self):
        return True  # Candidate readback never authorizes native execution or recovery.

    def retain_raw(self, call_index, stdout, stderr, receipt, *, exit_code, partial=b''):
        incoming = (call_index, stdout, stderr, receipt, exit_code, partial)
        # Independent private prefix survives validation, alias erasure and failures.
        if self.__pending is not None:
            self.rejected_raw = incoming
            self._failed(ValueError('batch original pending raw cannot be replaced'))
        self._fixed()
        held = {'incoming':incoming,'spans':None,'proof_raw':None,'error':None,
                'native_authorized':False,'formal_permission':False}
        self.__pending = self.pending = held
        self.__records = (*self.__records, held); self.records = self.__records
        self.__record_bindings = (*self.__record_bindings, (held,incoming,None))
        try:
            v.require(not self.__packing and self.__pack is None and type(call_index) is int and
                      call_index == len(self.__records)-1 < len(self.__maxima), 'batch raw exact next call')
            call = self.__request['calls'][call_index]; limits = self.__maxima[call_index]
            for name, raw in (('stdout',stdout), ('stderr',stderr), ('receipt',receipt), ('partial',partial)):
                v.require(type(raw) is bytes and len(raw) <= limits[name], 'batch original raw byte bound')
            v.require(type(exit_code) is int and -2147483648 <= exit_code <= 2147483647 and
                      len(receipt) > 0, 'batch literal receipt and declared exit')
            spans = []
            if exit_code == 0 and call['operation'] == 'head':
                v.require(stdout == (self.__request['revision']+'\n').encode('ascii'), 'batch exact head raw')
            if exit_code == 0 and call['operation'] == 'status':
                v.require(stdout == b'', 'batch clean status raw')
            if exit_code == 0 and call['operation'] == 'source_blob_batch':
                offset = 0
                for source_index in self.__request['groups'][call['group']]['members']:
                    row = self.__request['sources'][source_index]; size = row['pin']['bytes']
                    header = (row['git_blob_oid']+' blob '+str(size)+'\n').encode('ascii')
                    v.require(stdout[offset:offset+len(header)] == header, 'batch exact blob header/order/size')
                    start = offset + len(header); end = start + size
                    body = stdout[start:end]
                    v.require(len(body) == size and _batch_pin(body) == row['pin'] and
                              hashlib.sha1(b'blob '+str(size).encode()+b'\0'+body).hexdigest() ==
                              row['git_blob_oid'] and stdout[end:end+1] == b'\n',
                              'batch full original blob body/disk pin/object pin')
                    spans.append({'source':source_index,'start':start,'end':end,'pin':row['pin']})
                    offset = end+1
                v.require(offset == len(stdout) == call['stdout_bytes'], 'batch full stdout coverage')
            held['spans'] = spans
            proof = {'format':SOURCE_BATCH_PROOF,'request_pin':_batch_pin(self.__request_raw),
                     'call_index':call_index,'call':call,'exit_code':exit_code,
                     'raw_pins':{n:_batch_pin(r) for n,r in
                                 (('stdout',stdout),('stderr',stderr),('receipt',receipt),('partial',partial))},
                     'source_spans':spans,'scope':_batch_scope()}
            held['proof_raw'] = _batch_json(proof)  # Literal receipt is opaque, not native authentication.
            self.__record_bindings = (*self.__record_bindings[:-1], (held,incoming,held['proof_raw']))
            v.require(len(held['proof_raw']) <= 32768, 'batch proof candidate byte bound')
            if exit_code != 0:self._failed(ValueError('batch declared failure retains original raw prefix'))
            self.__pending = self.pending = None
            return held['proof_raw']
        except BaseException as error:
            held['error'] = error; self._failed(error)

    def prepare_pack(self):
        self._fixed()
        if self.__pack is not None:
            if self.__pack is not self.__pack_anchor:
                self._failed(ValueError('batch original cached packed return'))
            return self.__pack
        if self.__packing:self._failed(ValueError('batch packing cannot reenter'))
        self.__packing = True
        self.__pack_parts = ()
        try:
            v.require(self.__pending is None and len(self.__records) == len(self.__maxima),
                      'batch packed complete all-call raw coverage')
            header = b'SBR1'+len(self.__records).to_bytes(4,'little')
            self.__pack_parts = (header,); width = len(header)
            for held in self.__records:
                index, stdout, stderr, receipt, _, partial = held['incoming']
                parts = (index.to_bytes(4,'little') + b''.join(len(r).to_bytes(4,'little')
                         for r in (stdout,stderr,receipt,partial)), stdout,stderr,receipt,partial)
                width += sum(len(r) for r in parts)
                v.require(width <= self.maximum_packed_raw_bytes <= BATCH_PACK_MAX,
                          'batch original literal packed width')
                self.__pack_parts += parts
            self.__pack_raw = b''.join(self.__pack_parts)
            offset = 8
            for held in self.__records:
                index = int.from_bytes(self.__pack_raw[offset:offset+4],'little'); offset += 4
                lengths = [int.from_bytes(self.__pack_raw[offset+i:offset+i+4],'little') for i in range(0,16,4)]
                offset += 16
                v.require(index == held['incoming'][0], 'batch packed call order readback')
                for size, original in zip(lengths, (held['incoming'][1],held['incoming'][2],
                                                    held['incoming'][3],held['incoming'][5])):
                    returned = self.__pack_raw[offset:offset+size]; offset += size
                    v.require(returned == original, 'batch packed full literal raw readback')
            v.require(offset == len(self.__pack_raw), 'batch packed no trailing raw')
            self.__proof_raw = _batch_json({'format':SOURCE_BATCH_TRANSPORT,
                'request_pin':_batch_pin(self.__request_raw),'pack_pin':_batch_pin(self.__pack_raw),
                'call_proof_pins':[_batch_pin(h['proof_raw']) for h in self.__records],
                'raw_format':'SBR1-literal-no-compression','scope':_batch_scope()})
            self.__pack = self.__pack_anchor = (self.__pack_raw,self.__proof_raw)
            return self.__pack
        except BaseException as error:self._failed(error)

    def execute(self):
        self._failed(ValueError('batch candidate has no native operation or transport authority'))


SOURCE_OBJECT_REQUEST = 'anomaly-v03-source-object-batch-request-candidate-v1'
SOURCE_OBJECT_PROOF = 'anomaly-v03-source-object-batch-proof-candidate-v1'
SOURCE_OBJECT_TRANSPORT = 'anomaly-v03-source-object-batch-packed-raw-candidate-v1'
SOURCE_OBJECT_ARGV = ('git', 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)')


def source_object_batch_stdin(request, group_index):
    group = request['groups'][group_index]
    return ''.join(request['revision'] + ':' + request['sources'][i]['name'] + '\n'
                   for i in group['members']).encode('ascii')


def source_object_batch_request_candidate(*, revision, root, sources):
    """Declare tree lookup metadata, with source bodies retained independently."""
    _batch_digest(revision, 40)
    v.require(type(root) is str and 0 < len(root) <= 4096, 'object batch declared root')
    _batch_sources(sources)
    source_raw = _batch_json(list(sources))
    v.require(len(source_raw) <= 32768, 'object batch declared source byte bound')
    frozen = v.strict_json(source_raw)
    groups = []
    for start in range(0, len(frozen), BATCH_MEMBERS_MAX):
        members = list(range(start, min(start+BATCH_MEMBERS_MAX, len(frozen))))
        width = sum(47 + len(str(frozen[i]['pin']['bytes'])) for i in members)
        groups.append({'members': members, 'stdout_bytes': width})
    calls = []
    for phase in ('pre', 'post'):
        for operation in ('head', 'status'):
            calls.append({'phase': phase, 'operation': operation, 'group': None, 'stdout_bytes': None})
        for index, group in enumerate(groups):
            calls.append({'phase': phase, 'operation': 'source_blob_metadata_batch', 'group': index,
                          'stdout_bytes': group['stdout_bytes']})
    v.require(len(calls) <= BATCH_CALLS_MAX, 'object batch all planned call bound')
    value = {'format': SOURCE_OBJECT_REQUEST, 'revision': revision, 'root': root,
             'object_format': 'sha1', 'batch_argv': list(SOURCE_OBJECT_ARGV),
             'sources': frozen, 'groups': groups, 'calls': calls, 'scope': _batch_scope()}
    for index, group in enumerate(groups):
        group['stdin_pin'] = _batch_pin(source_object_batch_stdin(value, index))
    raw = _batch_json(value)
    v.require(len(raw) <= 32768, 'object batch request candidate byte bound')
    return raw


def _source_object_bodies(sources, bodies):
    v.require(type(bodies) is dict and set(bodies) == {s['name'] for s in sources},
              'object batch independent complete body roster')
    for row in sources:
        body = bodies[row['name']]
        v.require(type(body) is bytes and len(body) == row['pin']['bytes'] <= BATCH_STDOUT_MAX and
                  _batch_pin(body) == row['pin'] and
                  hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest() == row['git_blob_oid'],
                  'object batch independent SHA256 body and SHA1 blob pin')


def source_object_batch_stdout_candidate(*, request_raw, expected_sources, source_bodies,
                                        group_index, stdout):
    """Verify literal metadata against independently held bodies; no native authority."""
    v.require(type(request_raw) is bytes and 0 < len(request_raw) <= 32768,
              'object batch request raw bound')
    request = v.strict_json(request_raw)
    _batch_keys(request, 'format revision root object_format batch_argv sources groups calls scope',
                'object batch closed request fields')
    _batch_sources(expected_sources)
    _source_object_bodies(expected_sources, source_bodies)
    v.require(request['sources'] == list(expected_sources) and
              source_object_batch_request_candidate(revision=request['revision'], root=request['root'],
                  sources=expected_sources) == request_raw, 'object batch canonical independent request')
    v.require(type(group_index) is int and 0 <= group_index < len(request['groups']) and
              type(stdout) is bytes, 'object batch literal group return')
    group = request['groups'][group_index]
    v.require(_batch_pin(source_object_batch_stdin(request, group_index)) == group['stdin_pin'],
              'object batch exact tree pathname stdin')
    offset = 0; spans = []
    for index in group['members']:
        row = expected_sources[index]
        header = (row['git_blob_oid']+' blob '+str(row['pin']['bytes'])+'\n').encode('ascii')
        end = offset + len(header)
        v.require(stdout[offset:end] == header, 'object batch exact OID type size order newline')
        spans.append({'source': index, 'start': offset, 'end': end,
                      'source_pin': row['pin'], 'git_blob_oid': row['git_blob_oid']})
        offset = end
    v.require(offset == len(stdout) == group['stdout_bytes'], 'object batch full metadata stdout coverage')
    return _batch_json({'format': SOURCE_OBJECT_PROOF, 'request_pin': _batch_pin(request_raw),
                       'group': group_index, 'stdin_pin': group['stdin_pin'], 'stdout_pin': _batch_pin(stdout),
                       'source_spans': spans, 'git_body_returned': False, 'scope': _batch_scope()})


class SourceObjectBatchContractPreparation:
    """Same-owner memory candidates with full future raw/failure accounting.

    Metadata identifies tree blobs through independently held source bodies.
    Packing reduces file entry arithmetic. Literal raw bytes and original partial
    bytes remain separate from future archive growth; no compression is assumed.
    This class does not issue operations or publish/recover any native resource.
    """
    def _retain_inputs(self, *, owner, checkpoint, request_raw, expected_sources, source_bodies, raw_maxima,
                       storage_maxima):
        incoming = (owner, checkpoint, request_raw, expected_sources, source_bodies, raw_maxima, storage_maxima)
        if hasattr(self, '_SourceObjectBatchContractPreparation__inputs'):
            self.__rejected_inputs = self.rejected_inputs = incoming
            self._failed(ValueError('batch original preparation cannot be replaced'))
        self.__inputs = incoming
        self.original_inputs = incoming
        self.owner, self.checkpoint = owner, checkpoint
        self.__error = self.error = None
        self.__records = (); self.records = ()
        self.__raw_attempts = (); self.__rejected_preparations = ()
        self.__record_bindings = (); self.__metadata_bindings = ()
        self.__captures = (); self.raw_captures = self.__captures
        self.__capture_attempt = None
        self.__active_capture = None
        self.__pending = self.pending = None
        self.__packing = False
        self.__pack = None
        self.__pack_anchor = None
        self.__proof_raw = None
        self.__initialized = False

    def __init__(self, *, owner, checkpoint, request_raw, expected_sources, source_bodies, raw_maxima, storage_maxima):
        if not hasattr(self, '_SourceObjectBatchContractPreparation__inputs'):
            self._retain_inputs(owner=owner, checkpoint=checkpoint, request_raw=request_raw,
                                expected_sources=expected_sources, source_bodies=source_bodies, raw_maxima=raw_maxima,
                                storage_maxima=storage_maxima)
        if self.__initialized:self._failed(ValueError('batch original preparation initializes once'))
        self.__initialized = True
        try:
            v.require(all(a is b for a, b in zip(self.__inputs,
                (owner, checkpoint, request_raw, expected_sources, source_bodies, raw_maxima, storage_maxima))),
                'batch original inputs')
            v.require(type(request_raw) is bytes and 0 < len(request_raw) <= 32768,
                      'batch request raw bound')
            request = self.__request = v.strict_json(request_raw)
            _batch_keys(request, 'format revision root object_format batch_argv sources groups calls scope',
                        'batch closed request fields')
            v.require(request['format'] == SOURCE_OBJECT_REQUEST and request['object_format'] == 'sha1'
                      and request['scope'] == _batch_scope(), 'batch candidate format/scope')
            _batch_sources(expected_sources)
            _source_object_bodies(expected_sources, source_bodies)
            v.require(request['sources'] == list(expected_sources), 'batch independent exact source coverage')
            v.require(source_object_batch_request_candidate(revision=request['revision'], root=request['root'],
                sources=expected_sources) == request_raw, 'batch canonical complete ordered plan')
            self.__request_raw = request_raw
            v.require(type(raw_maxima) in (list, tuple) and len(raw_maxima) == len(request['calls']),
                      'batch all planned raw maxima')
            self.__maxima_raw = _batch_json(list(raw_maxima))
            self.__maxima = v.strict_json(self.__maxima_raw)
            maximum = 8 + 20 * len(raw_maxima)
            for call, limits in zip(request['calls'], self.__maxima):
                _batch_keys(limits, 'stdout stderr receipt partial', 'batch per-call failure maxima')
                for name, cap in (('stdout',131072), ('stderr',16384), ('receipt',32768), ('partial',131072)):
                    v.require(type(limits[name]) is int and 0 <= limits[name] <= cap, 'batch raw maximum bound')
                v.require(limits['receipt'] > 0 and (call['stdout_bytes'] is None or
                    limits['stdout'] >= call['stdout_bytes']), 'batch success and failure raw maxima')
                maximum += sum(limits.values())  # Includes every planned call, even completed calls.
            self.maximum_packed_raw_bytes = maximum
            self.__storage_raw = _batch_json(storage_maxima)
            _batch_keys(storage_maxima, 'control parent_failure diagnostic entry_context_identity '
                        'carrier_failure archive_new_growth partial_raw reserve snapshot', 'batch storage maxima')
            entries = {'control':14,'parent_failure':3,'diagnostic':2,'entry_context_identity':3,
                       'carrier_failure':2,'archive_new_growth':1,'partial_raw':1,'reserve':2}
            total_entries = 1; total_bytes = maximum  # One future literal call raw pack.
            for name, row in storage_maxima.items():
                _batch_keys(row, 'bytes entries', 'batch storage row')
                v.require(type(row['bytes']) is int and row['bytes'] >= 0 and
                          type(row['entries']) is int and row['entries'] >= 0, 'batch storage amounts')
                v.require(row['entries'] == entries[name] if name != 'snapshot' else row['entries'] <= 32,
                          'batch no completed entry discount')
                if name == 'reserve':
                    v.require(row['bytes'] == 131072, 'batch fixed reserve bytes')
                if name == 'archive_new_growth':
                    v.require(row['bytes'] <= 524288, 'batch independent archive growth cap')
                total_entries += row['entries']; total_bytes += row['bytes']
            self.projection = {'entries':total_entries,'bytes':total_bytes,
                               'packed_raw_bytes':maximum,'scope':_batch_scope()}
            v.require(maximum <= BATCH_PACK_MAX, 'batch packed future raw byte bound')
            v.require(total_entries <= 32 and total_bytes <= 1048576, 'batch full future storage bound')
        except BaseException as error:self._failed(error)

    def retain_rejected_preparation(self, held):
        if not self.__rejected_preparations:
            self.__rejected_preparations = (held,)
            self.rejected_preparation = held
        self._failed(ValueError('object batch original preparation cannot be replaced'))

    def _failed(self, error):
        if self.__error is None:self.__error = error
        self.error = self.__error
        self.__error.source_object_batch_preparation = self
        self.__error.reader_git_parent = self.__inputs[0]
        raise self.__error

    def _fixed(self):
        if self.__error is not None:raise self.__error
        try:
            v.require(self.original_inputs is self.__inputs and self.owner is self.__inputs[0] and
                      self.checkpoint is self.__inputs[1] and
                      self.__inputs[2] == self.__request_raw and
                      _batch_json(self.__request) == self.__request_raw and
                      _batch_json(list(self.__inputs[3])) == _batch_json(self.__request['sources']) and
                      _batch_json(list(self.__inputs[5])) == self.__maxima_raw and
                      _batch_json(self.__inputs[6]) == self.__storage_raw and
                      self.records is self.__records and self.pending is self.__pending,
                      'batch original private input/return bindings')
            _source_object_bodies(self.__request['sources'], self.__inputs[4])
            for held, metadata in self.__metadata_bindings:
                v.require(held['metadata_proof_raw'] is metadata, 'object batch original metadata proof return')
            for held, incoming, proof_raw in self.__record_bindings:
                v.require(held['incoming'] is incoming and held['proof_raw'] is proof_raw and
                          held['error'] is None and held['native_authorized'] is False and
                          held['formal_permission'] is False, 'batch original private raw/proof bindings')
            v.require(self.raw_captures is self.__captures, 'object batch original capture ledger')
            for capture in self.__captures:capture._fixed()
        except BaseException as error:self._failed(error)

    def unresolved(self):
        return True  # Candidate readback never authorizes native execution or recovery.

    def capture_raw(self, call_index, stdout, stderr, receipt, *, exit_code, partial=b''):
        """Read caller streams once; retain opaque receipt/partial independently."""
        if self.__error is not None:raise self.__error
        incoming = (self, call_index, stdout, stderr, receipt, exit_code, partial)
        if self.__captures and self.__captures[-1]._SourceObjectBatchRawCapture__inputs[1] == call_index:
            return self.__captures[-1].capture(incoming)
        held = SourceObjectBatchRawCapture.__new__(SourceObjectBatchRawCapture)
        held._retain(incoming)
        self.__capture_attempt = held
        try:
            self._fixed()
            v.require(type(call_index) is int and call_index == len(self.__records) < len(self.__maxima),
                      'object capture exact next call')
            self.__captures = (*self.__captures, held); self.raw_captures = self.__captures
            held._bind(self.__maxima[call_index], _batch_pin(self.__request_raw))
            self.__active_capture = held
            result = held.capture(incoming)
            self.__active_capture = None
            return result
        except BaseException as error:held._failed(error)

    def retain_raw(self, call_index, stdout, stderr, receipt, *, exit_code, partial=b'', _capture=None):
        incoming = (call_index, stdout, stderr, receipt, exit_code, partial)
        if self.__error is None:self.__raw_attempts = (*self.__raw_attempts, incoming)
        if self.__active_capture is not None and _capture is not self.__active_capture:
            self._failed(ValueError('object capture original raw forward cannot be replaced'))
        # Independent private prefix survives validation, alias erasure and failures.
        if self.__pending is not None:
            self.rejected_raw = incoming
            self._failed(ValueError('batch original pending raw cannot be replaced'))
        self._fixed()
        held = {'incoming':incoming,'spans':None,'proof_raw':None,'error':None,
                'native_authorized':False,'formal_permission':False}
        self.__pending = self.pending = held
        self.__records = (*self.__records, held); self.records = self.__records
        self.__record_bindings = (*self.__record_bindings, (held,incoming,None))
        try:
            v.require(not self.__packing and self.__pack is None and type(call_index) is int and
                      call_index == len(self.__records)-1 < len(self.__maxima), 'batch raw exact next call')
            call = self.__request['calls'][call_index]; limits = self.__maxima[call_index]
            for name, raw in (('stdout',stdout), ('stderr',stderr), ('receipt',receipt), ('partial',partial)):
                v.require(type(raw) is bytes and len(raw) <= limits[name], 'batch original raw byte bound')
            v.require(type(exit_code) is int and -2147483648 <= exit_code <= 2147483647 and
                      len(receipt) > 0, 'batch literal receipt and declared exit')
            spans = []
            if exit_code == 0 and call['operation'] == 'head':
                v.require(stdout == (self.__request['revision']+'\n').encode('ascii'), 'batch exact head raw')
            if exit_code == 0 and call['operation'] == 'status':
                v.require(stdout == b'', 'batch clean status raw')
            if exit_code == 0 and call['operation'] == 'source_blob_metadata_batch':
                metadata = source_object_batch_stdout_candidate(request_raw=self.__request_raw,
                    expected_sources=self.__request['sources'],source_bodies=self.__inputs[4],
                    group_index=call['group'],stdout=stdout)
                held['metadata_proof_raw'] = metadata
                self.__metadata_bindings = (*self.__metadata_bindings, (held,metadata))
                spans = v.strict_json(metadata)['source_spans']
            held['spans'] = spans
            proof = {'format':SOURCE_OBJECT_PROOF,'request_pin':_batch_pin(self.__request_raw),
                     'call_index':call_index,'call':call,'exit_code':exit_code,
                     'raw_pins':{n:_batch_pin(r) for n,r in
                                 (('stdout',stdout),('stderr',stderr),('receipt',receipt),('partial',partial))},
                     'source_spans':spans,'scope':_batch_scope()}
            held['proof_raw'] = _batch_json(proof)  # Literal receipt is opaque, not native authentication.
            self.__record_bindings = (*self.__record_bindings[:-1], (held,incoming,held['proof_raw']))
            v.require(len(held['proof_raw']) <= 32768, 'batch proof candidate byte bound')
            if exit_code != 0:self._failed(ValueError('batch declared failure retains original raw prefix'))
            self.__pending = self.pending = None
            return held['proof_raw']
        except BaseException as error:
            held['error'] = error; self._failed(error)

    def prepare_pack(self):
        self._fixed()
        if self.__pack is not None:
            if self.__pack is not self.__pack_anchor:
                self._failed(ValueError('batch original cached packed return'))
            return self.__pack
        if self.__packing:self._failed(ValueError('batch packing cannot reenter'))
        self.__packing = True
        self.__pack_parts = ()
        try:
            v.require(self.__pending is None and len(self.__records) == len(self.__maxima),
                      'batch packed complete all-call raw coverage')
            header = b'SOM1'+len(self.__records).to_bytes(4,'little')
            self.__pack_parts = (header,); width = len(header)
            for held in self.__records:
                index, stdout, stderr, receipt, _, partial = held['incoming']
                parts = (index.to_bytes(4,'little') + b''.join(len(r).to_bytes(4,'little')
                         for r in (stdout,stderr,receipt,partial)), stdout,stderr,receipt,partial)
                width += sum(len(r) for r in parts)
                v.require(width <= self.maximum_packed_raw_bytes <= BATCH_PACK_MAX,
                          'batch original literal packed width')
                self.__pack_parts += parts
            self.__pack_raw = b''.join(self.__pack_parts)
            offset = 8
            for held in self.__records:
                index = int.from_bytes(self.__pack_raw[offset:offset+4],'little'); offset += 4
                lengths = [int.from_bytes(self.__pack_raw[offset+i:offset+i+4],'little') for i in range(0,16,4)]
                offset += 16
                v.require(index == held['incoming'][0], 'batch packed call order readback')
                for size, original in zip(lengths, (held['incoming'][1],held['incoming'][2],
                                                    held['incoming'][3],held['incoming'][5])):
                    returned = self.__pack_raw[offset:offset+size]; offset += size
                    v.require(returned == original, 'batch packed full literal raw readback')
            v.require(offset == len(self.__pack_raw), 'batch packed no trailing raw')
            self.__proof_raw = _batch_json({'format':SOURCE_OBJECT_TRANSPORT,
                'request_pin':_batch_pin(self.__request_raw),'pack_pin':_batch_pin(self.__pack_raw),
                'call_proof_pins':[_batch_pin(h['proof_raw']) for h in self.__records],
                'raw_format':'SOM1-literal-no-compression','scope':_batch_scope()})
            self.__pack = self.__pack_anchor = (self.__pack_raw,self.__proof_raw)
            return self.__pack
        except BaseException as error:self._failed(error)

    def execute(self):
        self._failed(ValueError('batch candidate has no native operation or transport authority'))


class SourceObjectBatchRawCapture:
    """Original stream/read-return ledger; no close, exit or native authentication.

    Blocking reads and the caller's receipt/exit are engineering inputs. Bounded
    read requests do not establish native wall limits or global memory capacity.
    """
    def _retain(self, incoming):
        if hasattr(self, '_SourceObjectBatchRawCapture__inputs'):
            self._failed(ValueError('object capture original inputs initialize once'))
        self.__inputs = self.original_inputs = incoming
        self.__error = self.error = None
        self.__operations = self.operations = ()
        self.__prefixes = self.prefixes = ((), ())
        self.__pending = self.pending = None
        self.__running = False
        self.__result = self.__result_anchor = None
        self.__limits = None
        self.__descriptor = self.descriptor_raw = None
        self.__proof = None
        self.__rejected_inputs = None

    def _bind(self, limits, request_pin):
        v.require(self.__limits is None, 'object capture limits bind once')
        self.__limits = _batch_json(limits)
        self.__descriptor = self.descriptor_raw = _batch_json({
            'format':'anomaly-v03-source-object-raw-capture-candidate-v1',
            'request_pin':request_pin,'call_index':self.__inputs[1],
            'raw_maxima':limits,'read_chunk_bytes':4096,'read_attempts_per_stream':128,
            'detection_bytes_per_stream':1,'scope':_batch_scope()})

    def _failed(self, error):
        if self.__error is None:self.__error = error
        self.error = self.__error
        self.__error.source_object_raw_capture = self
        try:self.__inputs[0]._failed(self.__error)
        except BaseException as first:
            self.__error = self.error = first
            first.source_object_raw_capture = self
            raise

    def _fixed(self):
        if self.__error is not None:raise self.__error
        v.require(self.original_inputs is self.__inputs and self.operations is self.__operations and
                  self.prefixes is self.__prefixes and self.pending is self.__pending and
                  self.descriptor_raw is self.__descriptor and self.__result is self.__result_anchor,
                  'object capture original private return bindings')

    def _read(self, position, stream, cap):
        self.__pending = self.pending = ('read-getter', stream)
        read = stream.read
        self.__pending = self.pending = ('read-callable', stream, read)
        v.require(callable(read), 'object capture original read callable')
        size = 0
        for _ in range(128):
            self.__inputs[0]._fixed()
            requested = min(4096, cap + 1 - size)
            v.require(requested > 0, 'object capture original read detection bound')
            invocation = (position, stream, read, requested)
            self.__pending = self.pending = invocation
            old_operations, old_prefixes = self.__operations, self.__prefixes
            try:raw = read(requested)
            except BaseException as error:
                self.__operations = (*self.__operations, (invocation, False, None, error))
                if self.operations is old_operations:self.operations = self.__operations
                raise
            # Preserve the literal return before type/size checks or owner callbacks.
            self.__operations = (*self.__operations, (invocation, True, raw, None))
            if self.operations is old_operations:self.operations = self.__operations
            if type(raw) is bytes:
                parts = (*self.__prefixes[position], raw)
                self.__prefixes = (parts, self.__prefixes[1]) if position == 0 else (self.__prefixes[0], parts)
                if self.prefixes is old_prefixes:self.prefixes = self.__prefixes
            self.__inputs[0]._fixed()
            v.require(type(raw) is bytes and len(raw) <= requested, 'object capture bounded literal read return')
            size += len(raw)
            v.require(size <= cap, 'object capture raw exceeds independent maximum')
            if not raw:
                self.__pending = self.pending = None
                return b''.join(self.__prefixes[position])
        raise ValueError('object capture read attempt bound retains prefix')

    def capture(self, incoming):
        if self.__error is None and self.__rejected_inputs is None and (
                len(incoming) != len(self.__inputs) or not all(a is b for a, b in zip(incoming, self.__inputs))):
            self.__rejected_inputs = incoming
        try:
            self.__inputs[0]._fixed()
            self._fixed()
            v.require(len(incoming) == len(self.__inputs) and
                      all(a is b for a, b in zip(incoming, self.__inputs)), 'object capture same original inputs')
            if self.__result is not None:return self.__result
            v.require(not self.__running and self.__limits is not None, 'object capture cannot reenter')
            self.__running = True
            limits = v.strict_json(self.__limits)
            owner, index, stdout, stderr, receipt, exit_code, partial = self.__inputs
            for name, raw in (('receipt',receipt), ('partial',partial)):
                v.require(type(raw) is bytes and len(raw) <= limits[name], 'object capture independent opaque raw bound')
            v.require(receipt and type(exit_code) is int and -2147483648 <= exit_code <= 2147483647,
                      'object capture opaque receipt and declared exit')
            out = self._read(0, stdout, limits['stdout'])
            err = self._read(1, stderr, limits['stderr'])
            self.__raw = (index, out, err, receipt, exit_code, partial)
            self.__proof = owner.retain_raw(index, out, err, receipt, exit_code=exit_code, partial=partial,
                                           _capture=self)
            self.__result = self.__result_anchor = (self.__raw, self.__proof)
            return self.__result
        except BaseException as error:self._failed(error)

    def unresolved(self):return True
