"""Shared inputs for the scans: exact stock builds, checked by hash."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Analysis base of the decoded main block. Both bodies use the same one.
BASE = 0x60021020

MAINS = {
    'em5ii': ('fw/em5ii_4.1/00_0100_40300020.decoded.bin',
              'ecd9603c4a264a358d91ef110a05f9236055e6369399f7c7de5985b21a2fd96a'),
    'penf': ('fw/penf_3.1/00_0100_403a0020.decoded.bin',
             'a2eb1d1f1afe47cce148e9aae0a04dfb82547d9de9437d342e012341140913f4'),
}


def load_main(name):
    rel, expected = MAINS[name]
    path = ROOT / rel
    if not path.exists():
        sys.exit(f'{rel} is missing. See "Firmware inputs" in README.md.')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        sys.exit(f'{rel} is not the expected build.')
    return data


def addr(offset):
    return f'{BASE + offset:#x}'
