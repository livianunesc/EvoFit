#!/usr/bin/env python3
"""Ponte de login para rehash de contas antigas após a migração SQLite→MySQL."""
import hashlib
import hmac
import json
import re
import sys


def verify(payload):
    if not isinstance(payload, dict):
        return False
    value = payload.get("password")
    stored = payload.get("hash")
    if not isinstance(value, str) or not isinstance(stored, str):
        return False
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        return False
    if not 1 <= len(encoded) <= 4096:
        return False
    # Formato exato produzido pelo EvoFit original: 16 bytes salt + scrypt de 64 bytes.
    if not re.fullmatch(r"[0-9a-f]{32}:[0-9a-f]{128}", stored):
        return False
    salt, expected = stored.split(":", 1)
    try:
        actual = hashlib.scrypt(encoded, salt=salt.encode("ascii"), n=16384, r=8, p=1).hex()
    except (ValueError, MemoryError, AttributeError):
        return False
    return hmac.compare_digest(actual, expected)


def main():
    try:
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            result = False
        else:
            result = verify(json.loads(raw))
    except (ValueError, TypeError, UnicodeError, OSError):
        result = False
    sys.stdout.write("1" if result else "0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
