# Copyright Kevin Deldycke <kevin@deldycke.com> and contributors.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""Global binary cache for downloaded tool executables.

Caches platform-specific binaries under a user-level cache directory so that
repeated ``repomatic run <tool>`` invocations skip the download when the
version and platform match a previous run. Integrity is enforced by the caller
(``tool_runner._install_binary``) via SHA-256 re-verification on every cache
hit.

Cache layout::

    {cache_root}/bin/{tool}/{version}/{platform}/{executable}

.. note::
    The cache module is intentionally a pure storage layer. It does not know
    about checksums, registries, or tool specifications. All trust decisions
    (checksum verification, skip-checksum semantics) belong to the caller.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Config, load_repomatic_config


@dataclass(frozen=True)
class CacheEntry:
    """A single cached binary with its metadata."""

    tool: str
    """Tool name (registry key)."""

    version: str
    """Pinned version string."""

    platform: str
    """Platform key (e.g., ``linux-x64``, ``macos-arm64``)."""

    executable: str
    """Executable filename."""

    size: int
    """File size in bytes."""

    path: Path
    """Absolute path to the cached binary."""

    mtime: float
    """File modification time (seconds since epoch)."""


def _platform_cache_dir() -> Path:
    """Return the platform-appropriate default cache directory.

    - macOS: ``~/Library/Caches/repomatic``.
    - Windows: ``%LOCALAPPDATA%\\repomatic\\Cache``.
    - Linux/POSIX: ``$XDG_CACHE_HOME/repomatic`` or ``~/.cache/repomatic``.
    """
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / "repomatic"
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "repomatic" / "Cache"
        return home / "AppData" / "Local" / "repomatic" / "Cache"
    # Linux and other POSIX.
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "repomatic"
    return home / ".cache" / "repomatic"


def cache_dir() -> Path:
    """Resolve the cache root directory.

    Precedence (highest to lowest):

    1. ``REPOMATIC_CACHE_DIR`` environment variable.
    2. ``cache.dir`` in ``[tool.repomatic]``.
    3. Platform-specific default.

    :return: Absolute path to the cache root (may not exist yet).
    """
    # 1. Environment variable (highest priority).
    env_override = os.environ.get("REPOMATIC_CACHE_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()

    # 2. Config from [tool.repomatic].
    config = load_repomatic_config()
    if config.cache_dir:
        return Path(config.cache_dir).expanduser().resolve()

    # 3. Platform default.
    return _platform_cache_dir()


def _bin_dir() -> Path:
    """Return the ``bin/`` subdirectory under the cache root."""
    return cache_dir() / "bin"


def cached_binary_path(
    name: str,
    version: str,
    platform_key: str,
    executable: str,
) -> Path:
    """Construct the cache path for a binary (does not check existence).

    :param name: Tool name.
    :param version: Pinned version.
    :param platform_key: Platform key (e.g., ``linux-x64``).
    :param executable: Executable filename.
    :return: Absolute path where the binary would be cached.
    """
    return _bin_dir() / name / version / platform_key / executable


def get_cached_binary(
    name: str,
    version: str,
    platform_key: str,
    executable: str,
) -> Path | None:
    """Return the cached binary path if it exists and is executable.

    Does **not** verify the checksum. The caller is responsible for integrity
    checks since it owns the checksum value and the ``skip_checksum`` flag.

    :param name: Tool name.
    :param version: Pinned version.
    :param platform_key: Platform key.
    :param executable: Executable filename.
    :return: Path to the cached binary, or ``None`` if not cached.
    """
    path = cached_binary_path(name, version, platform_key, executable)
    if path.is_file() and os.access(path, os.X_OK):
        return path
    return None


def store_binary(
    name: str,
    version: str,
    platform_key: str,
    source: Path,
) -> Path:
    """Copy an extracted binary into the cache atomically.

    Writes to a temporary file in the target directory, then renames to the
    final name. This is atomic on POSIX (same-filesystem rename) and safe on
    Windows (``Path.replace`` overwrites atomically).

    Triggers :func:`auto_purge` after a successful store.

    :param name: Tool name.
    :param version: Pinned version.
    :param platform_key: Platform key.
    :param source: Path to the extracted binary to cache.
    :return: Path to the cached binary.
    """
    dest = cached_binary_path(name, version, platform_key, source.name)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: temp file in same directory, then rename.
    fd, tmp = tempfile.mkstemp(
        dir=dest.parent,
        prefix=f".{source.name}.",
        suffix=".tmp",
    )
    try:
        os.close(fd)
        tmp_path = Path(tmp)
        shutil.copy2(source, tmp_path)
        tmp_path.chmod(0o755)
        tmp_path.replace(dest)
    except BaseException:
        # Clean up partial writes on any failure.
        Path(tmp).unlink(missing_ok=True)
        raise

    logging.debug("Cached %s %s for %s at %s.", name, version, platform_key, dest)
    auto_purge()
    return dest


def cache_info() -> list[CacheEntry]:
    """List all cached binaries.

    :return: List of :class:`CacheEntry` instances, sorted by tool name then
        version.
    """
    bin_root = _bin_dir()
    if not bin_root.is_dir():
        return []

    entries: list[CacheEntry] = []
    for tool_dir in sorted(bin_root.iterdir()):
        if not tool_dir.is_dir():
            continue
        for version_dir in sorted(tool_dir.iterdir()):
            if not version_dir.is_dir():
                continue
            for platform_dir in sorted(version_dir.iterdir()):
                if not platform_dir.is_dir():
                    continue
                for binary in sorted(platform_dir.iterdir()):
                    if not binary.is_file():
                        continue
                    stat = binary.stat()
                    entries.append(CacheEntry(
                        tool=tool_dir.name,
                        version=version_dir.name,
                        platform=platform_dir.name,
                        executable=binary.name,
                        size=stat.st_size,
                        path=binary,
                        mtime=stat.st_mtime,
                    ))
    return entries


def clear_cache(
    tool: str | None = None,
    max_age_days: int | None = None,
) -> tuple[int, int]:
    """Remove cached binaries.

    :param tool: If set, only remove entries for this tool. Otherwise remove
        all cached binaries.
    :param max_age_days: If set, only remove entries with mtime older than
        this many days. Otherwise remove all matching entries.
    :return: Tuple of (files_deleted, bytes_freed).
    """
    bin_root = _bin_dir()
    if not bin_root.is_dir():
        return 0, 0

    cutoff = time.time() - (max_age_days * 86400) if max_age_days is not None else None
    files_deleted = 0
    bytes_freed = 0

    for entry in cache_info():
        if tool is not None and entry.tool != tool:
            continue
        if cutoff is not None and entry.mtime >= cutoff:
            continue
        logging.debug("Purging cached binary: %s", entry.path)
        try:
            bytes_freed += entry.size
            entry.path.unlink()
            files_deleted += 1
        except OSError:
            logging.debug("Failed to remove %s.", entry.path)

    # Prune empty parent directories up to bin_root.
    _prune_empty_dirs(bin_root)
    return files_deleted, bytes_freed


def _prune_empty_dirs(root: Path) -> None:
    """Remove empty directories under *root*, bottom-up."""
    if not root.is_dir():
        return
    # Walk bottom-up and attempt to remove each directory. rmdir() fails
    # (OSError) if the directory is non-empty, which is the desired behavior.
    for dirpath, _dirnames, _filenames in os.walk(root, topdown=False):
        path = Path(dirpath)
        if path == root:
            continue
        try:
            path.rmdir()
        except OSError:
            pass


def _max_age_days() -> int:
    """Resolve the auto-purge TTL.

    Precedence (highest to lowest):

    1. ``REPOMATIC_CACHE_MAX_AGE`` environment variable.
    2. ``cache.max-age`` in ``[tool.repomatic]``.
    3. ``Config.cache_max_age`` field default.

    :return: TTL in days. ``0`` means auto-purge is disabled.
    """
    # 1. Environment variable (highest priority).
    raw = os.environ.get("REPOMATIC_CACHE_MAX_AGE", "")
    if raw.strip():
        try:
            return int(raw)
        except ValueError:
            logging.warning(
                "Invalid REPOMATIC_CACHE_MAX_AGE=%r, using config default.",
                raw,
            )

    # 2 + 3. Config from [tool.repomatic] (falls back to field default).
    config = load_repomatic_config()
    return config.cache_max_age


def auto_purge() -> None:
    """Remove cached entries older than the configured TTL.

    Called automatically after :func:`store_binary`. Resolves the TTL from
    ``REPOMATIC_CACHE_MAX_AGE`` env var, then ``cache.max-age`` in
    ``[tool.repomatic]``, then the ``Config.cache_max_age`` field default.
    Set to ``0`` to disable.
    """
    days = _max_age_days()
    if days <= 0:
        return
    deleted, freed = clear_cache(max_age_days=days)
    if deleted:
        logging.debug(
            "Auto-purged %d cached binary(ies), freed %d bytes.", deleted, freed
        )
