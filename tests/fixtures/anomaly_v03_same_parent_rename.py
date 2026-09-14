"""Explicit same-parent NT leaf rename; held-parent mode stays unchanged."""
import struct

from . import anomaly_v03_directory_rename as directory


def same_parent_request():
    """Fixed Win64 payload leaf; NULL RootDirectory means source's parent.

    No path, parent, flags or step is supplied by the caller. The live source
    and held parent remain bound/observed by the inherited directory operation.
    """
    name = "payload".encode("utf-16-le")
    return struct.pack("<I4xQI", 0, 0, len(name)) + name + b"\0\0"


class SameParentDirectoryRename(directory.DirectoryRename):
    def __init__(self, backend, *, group, previous, files):
        super().__init__(backend, group=group, previous=previous, files=files, parent_policy="frozen")
        self._request = same_parent_request()

    def snapshot(self):
        result = super().snapshot()
        result.update(name_resolution="source_parent", root_directory_is_null=True)
        return result


class WindowsNtSameParentBackend(directory.WindowsNtDirectoryBackend):
    """Accept only the fixed same-parent wire; no failure-time API fallback."""
    def _matches_request(self, raw):
        return type(raw) is bytes and raw == same_parent_request()

    def native_snapshot(self):
        result = super().native_snapshot()
        result.update(name_resolution="source_parent", root_directory_is_null=True)
        return result
