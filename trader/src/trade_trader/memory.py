"""Filesystem backend for the Trader's memory.

The Anthropic memory tool addresses files as ``/memories/<path>``. This store
maps that namespace onto one directory, ``<TRADE_DATA_DIR>/trader/memory``, and
refuses anything that would resolve outside it: absolute paths elsewhere,
``..`` segments, NUL bytes, and symlinks that point out of the root.

Memory contents are data. Nothing in this module interprets them.
"""

from __future__ import annotations

import builtins
from pathlib import Path, PurePosixPath

MEMORY_PREFIX = "/memories"
MAX_FILE_BYTES = 1_000_000
"""A single memory file may not exceed this size; the Trader must summarize instead."""

DEFAULT_FILES: dict[str, str] = {
    "lessons.md": "# Lessons\n\nWhat worked, with the run that showed it.\n",
    "playbook.md": "# Playbook\n\nStrategy patterns worth reusing, and when.\n",
    "mistakes.md": "# Mistakes\n\nReread in full before every proposal. Never delete entries.\n",
}
"""Files every memory directory starts with. ``symbols/<SYM>.md`` are created on demand."""


class MemoryPathError(ValueError):
    """A memory path would escape the store or is otherwise malformed."""


class MemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    # -- paths ---------------------------------------------------------------

    def resolve(self, path: str) -> Path:
        """Map a memory-tool path to a real path inside the root, or raise.

        Accepts ``/memories/x/y.md`` and root-relative ``x/y.md``. Returns the
        root itself for ``/memories`` or ``""``.
        """
        if "\x00" in path:
            raise MemoryPathError("path contains a NUL byte")
        rel = path.strip()
        if rel.startswith(MEMORY_PREFIX):
            rel = rel[len(MEMORY_PREFIX) :]
            if rel and not rel.startswith("/"):
                raise MemoryPathError(f"{path!r} is not under {MEMORY_PREFIX}/")
            rel = rel.lstrip("/")
        elif rel.startswith("/"):
            raise MemoryPathError(f"absolute path {path!r} is outside {MEMORY_PREFIX}")
        posix = PurePosixPath(rel)  # normalizes "." segments; keeps ".."
        if ".." in posix.parts:
            raise MemoryPathError(f"{path!r} contains a '..' segment")
        if "\\" in rel:
            raise MemoryPathError(f"{path!r} contains a backslash")
        candidate = self.root.joinpath(*posix.parts)
        resolved = candidate.resolve()
        if resolved != self.root and not resolved.is_relative_to(self.root):
            raise MemoryPathError(f"{path!r} resolves outside the memory root")
        return resolved

    def to_memory_path(self, real: Path) -> str:
        """Inverse of ``resolve``: a real path under the root as ``/memories/...``."""
        rel = real.resolve().relative_to(self.root).as_posix()
        return MEMORY_PREFIX if rel == "." else f"{MEMORY_PREFIX}/{rel}"

    # -- operations ----------------------------------------------------------

    def exists(self, path: str) -> bool:
        return self.resolve(path).exists()

    def read(self, path: str) -> str:
        target = self.resolve(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        return target.read_text(encoding="utf-8")

    def write(self, path: str, text: str) -> None:
        target = self.resolve(path)
        if target == self.root or target.is_dir():
            raise MemoryPathError(f"{path!r} is a directory")
        data = text.encode("utf-8")
        if len(data) > MAX_FILE_BYTES:
            raise ValueError(f"{path!r} would be {len(data)} bytes; limit is {MAX_FILE_BYTES}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def delete(self, path: str) -> None:
        target = self.resolve(path)
        if target == self.root:
            raise MemoryPathError("refusing to delete the memory root")
        if not target.is_file():
            raise FileNotFoundError(path)
        target.unlink()

    def list(self, path: str = MEMORY_PREFIX) -> builtins.list[str]:
        """Every file under ``path`` (recursive), as sorted ``/memories/...`` paths."""
        base = self.resolve(path)
        if not base.is_dir():
            return []
        return sorted(
            self.to_memory_path(p)
            for p in base.rglob("*")
            if p.is_file() and p.resolve().is_relative_to(self.root)
        )

    def bootstrap(self) -> builtins.list[str]:
        """Create the root, ``symbols/``, and any missing default file. Idempotent."""
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "symbols").mkdir(exist_ok=True)
        missing = [name for name in DEFAULT_FILES if not (self.root / name).exists()]
        for name in missing:
            (self.root / name).write_text(DEFAULT_FILES[name], encoding="utf-8")
        return [f"{MEMORY_PREFIX}/{name}" for name in missing]
