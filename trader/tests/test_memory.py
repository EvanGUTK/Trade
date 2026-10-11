from __future__ import annotations

import os
from pathlib import Path

import pytest

from trade_trader.memory import (
    DEFAULT_FILES,
    MAX_FILE_BYTES,
    MEMORY_PREFIX,
    MemoryPathError,
    MemoryStore,
)


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory")


def test_round_trip_and_listing(store: MemoryStore) -> None:
    store.write("/memories/lessons.md", "# Lessons\n")
    store.write("symbols/SPY.md", "trend follower\n")
    assert store.read("/memories/lessons.md") == "# Lessons\n"
    assert store.read("/memories/symbols/SPY.md") == "trend follower\n"
    assert store.exists("lessons.md")
    assert store.list() == ["/memories/lessons.md", "/memories/symbols/SPY.md"]
    assert store.list("/memories/symbols") == ["/memories/symbols/SPY.md"]
    assert store.list("/memories/nope") == []
    store.delete("/memories/symbols/SPY.md")
    assert store.list() == ["/memories/lessons.md"]


@pytest.mark.parametrize(
    "path",
    [
        "../outside.md",
        "/memories/../outside.md",
        "/memories/a/../../outside.md",
        "/etc/passwd",
        "/memoriesX/evil.md",
        "a\\..\\b.md",
        "bad\x00name.md",
    ],
)
def test_traversal_and_malformed_paths_are_rejected(store: MemoryStore, path: str) -> None:
    with pytest.raises(MemoryPathError):
        store.resolve(path)
    with pytest.raises(MemoryPathError):
        store.write(path, "x")
    with pytest.raises(MemoryPathError):
        store.read(path)


def test_symlink_escape_is_rejected(store: MemoryStore, tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("secret")
    store.root.mkdir(parents=True)
    link = store.root / "link.md"
    os.symlink(outside, link)
    with pytest.raises(MemoryPathError, match="outside"):
        store.read("/memories/link.md")
    assert store.list() == []  # escaped symlinks are not listed either


def test_root_is_not_a_file(store: MemoryStore) -> None:
    assert store.resolve("/memories") == store.root
    assert store.resolve("") == store.root
    assert store.resolve("a/./b.md") == store.root / "a" / "b.md"  # "." is harmless
    with pytest.raises(MemoryPathError, match="directory"):
        store.write("/memories", "x")
    with pytest.raises(MemoryPathError, match="root"):
        store.delete("")


def test_size_limit(store: MemoryStore) -> None:
    with pytest.raises(ValueError, match="limit"):
        store.write("big.md", "x" * (MAX_FILE_BYTES + 1))


def test_bootstrap_is_idempotent(store: MemoryStore) -> None:
    created = store.bootstrap()
    assert created == [f"{MEMORY_PREFIX}/{name}" for name in DEFAULT_FILES]
    assert (store.root / "symbols").is_dir()
    store.write("mistakes.md", "# Mistakes\n\n- 2026-10-10: traded on a partial SMA window\n")
    assert store.bootstrap() == []
    assert "partial SMA" in store.read("mistakes.md")
