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
         'native_policy': 'loaded-images-under-python-or-windows-system32'}


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


def _location(path, root, base, windows, *, native=False):
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
    v.require(native and path.is_relative_to(windows), 'dependency outside permitted observation roots')
    return 'windows-system32/' + path.relative_to(windows).as_posix(), 'native'


def _inventory(root):
    base, windows = Path(sys.base_prefix), system32()
    # Load enumeration libraries before taking the module list.
    images = windows_modules()
    files, physical, modules = {}, {}, {}

    def add(path, *, native=False, cache=False):
        path = Path(path)
        logical, category = _location(path, root, base, windows, native=native)
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
            logical, category = _location(path, root, base, windows, native=row['native'])
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
