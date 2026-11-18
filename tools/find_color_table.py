#!/usr/bin/env python3
"""Locate the shared COLOR table in the E-M5 II main block and list who points at it.

The 3,028-byte table is byte-identical on PEN-F, E-P7 and OM-3
(oly_fw_analysis, docs/color/pen-f/HSL_TABLES.md). This scan shows the E-M5 II
carries it too, inside a run of same-sized tables, and that no 32-bit pointer
in the main block refers to it.
"""
import hashlib
import struct
import sys

from common import BASE, addr, load_main

TABLE_BYTES = 3028
TABLE_SHA = 'a33d64bdb78ac41ba24ccbff820380f563211a095ac08a12a7c37a51b5c00531'
PENF_TABLE = 0x60622d74
EXPECTED_OFFSET = 0x5ffef4  # 0x60620f14


def find_table(data):
    view = memoryview(data)
    return [o for o in range(0, len(data) - TABLE_BYTES, 4)
            if hashlib.sha256(view[o:o + TABLE_BYTES]).hexdigest() == TABLE_SHA]


def pointers_into(data, lo, hi):
    """Every little-endian u32 in the image whose value lies in [lo, hi)."""
    found = {}
    for o in range(len(data) - 3):
        value = struct.unpack_from('<I', data, o)[0]
        if lo <= value < hi:
            found.setdefault(value, []).append(o)
    return found


def main():
    em5 = load_main('em5ii')
    penf = load_main('penf')

    hits = find_table(em5)
    print('COLOR table offsets:', [hex(o) for o in hits])
    if hits != [EXPECTED_OFFSET]:
        sys.exit('COLOR table not found exactly once at the recorded offset.')
    table = BASE + hits[0]
    print('COLOR table address:', hex(table))

    # Neighbours are same-sized tables. List pointers to each slot around COLOR.
    near = pointers_into(em5, table - 5 * TABLE_BYTES, table + 2 * TABLE_BYTES)
    print('\nslot  address      pointers from')
    for slot in range(-5, 2):
        a = table + slot * TABLE_BYTES
        refs = [addr(o) for o in near.get(a, [])]
        label = '  <- COLOR' if slot == 0 else ''
        print(f'{slot:+d}    {a:#x}   {refs or "none"}{label}')
    if near.get(table):
        sys.exit('Unexpected: something points at the COLOR table.')

    # The table that follows COLOR is the same on both bodies.
    p = PENF_TABLE - BASE + TABLE_BYTES
    e = hits[0] + TABLE_BYTES
    same_next = penf[p:p + TABLE_BYTES] == em5[e:e + TABLE_BYTES]
    print('\nTable after COLOR identical to PEN-F:', same_next)
    if not same_next:
        sys.exit('Following table differs from PEN-F.')


if __name__ == '__main__':
    main()
