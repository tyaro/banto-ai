"""Prepare a documentation index update without editing files or running Git."""
from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

DEFAULT_SECTION = "v0.3の少量devモデル評価"
DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs"
_LINK = re.compile(r"^- \[([^\[\]\n]+)\]\(([^\s)]+)\)[ \t]*$")


def _local_target(index: Path, href: str) -> Path:
    url = urlsplit(href)
    if url.scheme or url.netloc or url.query or url.fragment or "\\" in href:
        raise ValueError("report links must be local relative paths")
    path = Path(unquote(url.path))
    if path.is_absolute():
        raise ValueError("report links must be relative")
    return (index.parent / path).resolve()


def render_result_index(original: str, *, index_path: Path, report_path: Path,
                        title: str, section: str = DEFAULT_SECTION) -> str:
    """Return LF Markdown; find the section semantically and count its links.

    No old count, previous report title, hash, seed, or template source is used.
    Filesystem existence checks belong to prepare_result_index below.
    """
    if not title or any(c in title for c in "[]\r\n"):
        raise ValueError("title must be one nonempty Markdown link label")
    if not section or any(c in section for c in "\r\n"):
        raise ValueError("section must be one nonempty heading")
    index, report = Path(index_path).resolve(), Path(report_path).resolve()
    text = original.replace("\r\n", "\n")
    if "\r" in text or text.startswith("\ufeff"):
        raise ValueError("index must be UTF-8 Markdown without BOM or bare CR")
    lines = text.splitlines(keepends=True)
    heading = re.compile(r"## " + re.escape(section) + r"(?:（[0-9]+件）)?[ \t]*$")
    starts = [i for i, line in enumerate(lines) if heading.fullmatch(line.rstrip("\n"))]
    if len(starts) != 1:
        raise ValueError(f"expected one index section: {section}; found {len(starts)}")
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = "".join(lines[start + 1:end])
    entries = []
    for line in body.splitlines():
        if line.startswith(("```", "~~~")):
            raise ValueError("index section must not contain code blocks")
        if line.startswith("- "):
            link = _LINK.fullmatch(line)
            if link is None:
                raise ValueError("index section contains a malformed report link")
            label, href = link.groups()
            entries.append((label, _local_target(index, href)))
    targets = [target for _, target in entries]
    if len(set(targets)) != len(targets):
        raise ValueError("index section contains duplicate report targets")
    matches = [label for label, target in entries if target == report]
    if matches and matches != [title]:
        raise ValueError("existing report link has a different title")
    if any(label == title and target != report for label, target in entries):
        raise ValueError("report title is already linked to another file")
    if not matches:
        relative = os.path.relpath(report, index.parent).replace(os.sep, "/")
        href = quote(relative, safe="/-._~")
        body = "\n- [" + title + "](" + href + ")\n\n" + body.lstrip("\n")
    count = len(entries) + (0 if matches else 1)
    return "".join(lines[:start]) + f"## {section}（{count}件）\n" + body + "".join(lines[end:])


def prepare_result_index(index_path: Path, report_path: Path, title: str, *,
                         section: str = DEFAULT_SECTION, docs_root: Path = DOCS_ROOT,
                         pending_report: bytes | None = None) -> bytes:
    """Validate current paths and return prospective bytes before any write.

    A new report can be passed as pending UTF-8 bytes by the document builder;
    it must not already exist. Existing reports are checked from disk.
    """
    index, report, root = (Path(p).resolve() for p in (index_path, report_path, docs_root))
    if any(not p.is_relative_to(root) or p.suffix != ".md" for p in (index, report)):
        raise ValueError("index and report must be Markdown files inside docs_root")
    if index == report:
        raise ValueError("report must differ from index")
    original = index.read_bytes().decode("utf-8")
    if pending_report is None:
        report.read_bytes().decode("utf-8")
    else:
        if type(pending_report) is not bytes:
            raise TypeError("pending_report must be UTF-8 bytes")
        if report.exists():
            raise FileExistsError("pending report already exists")
        pending_report.decode("utf-8")
    return render_result_index(original, index_path=index, report_path=report,
                               title=title, section=section).encode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DOCS_ROOT / "results/README.md")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--section", default=DEFAULT_SECTION)
    parser.add_argument("--docs-root", type=Path, default=DOCS_ROOT)
    parser.add_argument("--check", action="store_true", help="exit 1 if an update is needed")
    args = parser.parse_args(argv)
    try:
        original = args.index.read_bytes()
        updated = prepare_result_index(args.index, args.report, args.title,
                                       section=args.section, docs_root=args.docs_root)
    except (ValueError, OSError) as error:
        parser.exit(2, f"index preparation failed: {error}\n")
    diff = difflib.unified_diff(original.decode().splitlines(keepends=True),
                               updated.decode().splitlines(keepends=True),
                               fromfile=str(args.index), tofile=str(args.index))
    sys.stdout.buffer.write("".join(diff).encode("utf-8"))
    return 1 if args.check and original != updated else 0


if __name__ == "__main__":
    raise SystemExit(main())
