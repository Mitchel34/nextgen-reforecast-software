"""Bounded, resident-only helpers for the separate public physical reference."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from datetime import datetime, timezone

SHA = re.compile(r"[0-9a-f]{64}", re.ASCII)
DECIMAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", re.ASCII)


class ReferenceError(ValueError):
    pass


def pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ReferenceError("duplicate JSON key")
        result[key] = value
    return result


def nonfinite(value):
    raise ReferenceError("nonfinite JSON constant")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def regular(path, maximum):
    path = Path(path).absolute()
    for parent in [*reversed(path.parents), path]:
        s = parent.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s, "st_flags", 0) & 0x40000000:
            raise ReferenceError("symlink or dataless path refused")
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or not 0 <= s.st_size <= maximum:
        raise ReferenceError("regular resident file byte bound exceeded")
    return path


def read(path, maximum=16 * 1024 * 1024):
    path = regular(path, maximum)
    before = path.stat()
    with path.open("rb") as source:
        raw = source.read(maximum + 1)
    if len(raw) > maximum:
        raise ReferenceError("file grew beyond the bounded read allowance")
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ReferenceError("file changed during bounded read")
    return raw


def binding(path, maximum=1024 * 1024 * 1024):
    path = regular(path, maximum)
    before = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ReferenceError("file changed during hashing")
    return {"bytes": before.st_size, "sha256": h.hexdigest()}


def load(path, maximum=16 * 1024 * 1024):
    return json.loads(read(path, maximum), object_pairs_hook=pairs, parse_constant=nonfinite)


def seal(value, field):
    value = dict(value)
    if field in value:
        raise ReferenceError("identity field already present")
    value[field] = hashlib.sha256(canonical(value)).hexdigest()
    return value


def verify(value, field):
    copy = dict(value)
    expected = copy.pop(field, None)
    if not isinstance(expected, str) or not SHA.fullmatch(expected) or hashlib.sha256(canonical(copy)).hexdigest() != expected:
        raise ReferenceError("sealed document identity differs")
    return value


def write_new(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def utc(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ReferenceError("canonical UTC timestamp required")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def number(value):
    if not isinstance(value, str) or not DECIMAL.fullmatch(value.strip()) or not math.isfinite(float(value)):
        raise ReferenceError("malformed or nonfinite numeric output")
    return float(value)


def relative(value):
    if not isinstance(value, str) or not value or "\\" in value or Path(value).is_absolute() or any(p in (".", "..", "") for p in value.split("/")):
        raise ReferenceError("unsafe relative artifact path")
    return value


def inventory(root, maximum_bytes, maximum_files=4096, hash_files=True):
    root = Path(root).absolute()
    s = root.lstat()
    if not stat.S_ISDIR(s.st_mode) or getattr(s, "st_flags", 0) & 0x40000000:
        raise ReferenceError("resident directory required")
    result = []
    total = 0
    pending = [root]
    while pending:
        folder = pending.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                p = Path(entry.path)
                s = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(s.st_mode) or getattr(s, "st_flags", 0) & 0x40000000:
                    raise ReferenceError("symlink or dataless output refused")
                if stat.S_ISDIR(s.st_mode):
                    pending.append(p)
                elif stat.S_ISREG(s.st_mode):
                    total += s.st_size
                    if total > maximum_bytes or len(result) >= maximum_files:
                        raise ReferenceError("output inventory bound exceeded")
                    result.append({"path": p.relative_to(root).as_posix(),
                                   **(binding(p, maximum_bytes) if hash_files else {"bytes": s.st_size})})
                else:
                    raise ReferenceError("special output file refused")
    return sorted(result, key=lambda r: r["path"])
