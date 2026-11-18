#!/usr/bin/env python3
"""Look for PEN-F COLOR code in the E-M5 II main block.

Method: slide a 10-byte window over a PEN-F function and count the windows
that occur exactly once in the E-M5 II image. Windows that agree on one
displacement point at the matching function. Absolute addresses inside
instructions differ between builds, so a true twin scores high but not 100%.

This is a byte-pattern survey, not disassembly. A low score means "no close
twin", not "no equivalent code".
"""
import collections
import struct
import sys

from common import BASE, load_main

WINDOW = 10

# PEN-F 3101 addresses from oly_fw_analysis (compare_color_generations.py and
# docs/color/pen-f/EDITOR.md). Lengths for the editor entries are a fixed span
# from the entry point, not measured function sizes.
TARGETS = [
    # name, start, length, group
    ('ISP writer', 0x604b5006, 0x604b51de - 0x604b5006, 'pipeline'),
    ('table selector', 0x604f747f, 0x604f7572 - 0x604f747f, 'pipeline'),
    ('COLOR builder', 0x604f7272, 0x604f746a - 0x604f7272, 'pipeline'),
    ('editor local handler', 0x60cefd3d, 0x300, 'editor'),
    ('editor state entry', 0x60cefa1d, 0x300, 'editor'),
    ('GUI setter', 0x607363b3, 0x200, 'editor'),
    ('settings manager', 0x6075fbed, 0x200, 'editor'),
    ('COLOR up/down', 0x60cb0684, 0x400, 'editor'),
    ('wheel viewer constructor', 0x60c84664, 0x29d, 'editor'),
    ('wheel viewer update', 0x60c84901, 0x300, 'editor'),
    ('wheel draw command', 0x6081b780, 0x300, 'editor'),
    ('Draw_C3d_Async', 0x60300b3d, 0x200, 'editor'),
    ('C3d value conversion', 0x602fc370, 0x200, 'editor'),
]

PENF_GAIN_POINTERS = 0x6062fef8


def score(penf, em5, start, length):
    segment = penf[start - BASE:start - BASE + length]
    displacement = collections.Counter()
    total = len(segment) - WINDOW
    for i in range(total):
        chunk = segment[i:i + WINDOW]
        j = em5.find(chunk)
        if j >= 0 and em5.find(chunk, j + 1) < 0:
            displacement[j - i] += 1
    best = displacement.most_common(1)
    where, agree = (BASE + best[0][0], best[0][1]) if best else (None, 0)
    return sum(displacement.values()), total, where, agree


def main():
    penf = load_main('penf')
    em5 = load_main('em5ii')

    results = {}
    print(f'{"PEN-F function":26s} {"PEN-F":>10s}  {"hits":>9s}  best E-M5 II twin')
    for name, start, length, _ in TARGETS:
        hits, total, where, agree = score(penf, em5, start, length)
        results[name] = hits / total
        twin = f'{where:#x} ({agree} agree)' if where else '-'
        print(f'{name:26s} {start:#10x}  {hits:4d}/{total:<4d}  {twin}')

    # Saturation gains: twelve pointers to (u16, u16) pairs.
    pointers = struct.unpack_from('<12I', penf, PENF_GAIN_POINTERS - BASE)
    lo, hi = min(pointers), max(pointers) + 4
    blob = penf[lo - BASE:hi - BASE]
    gains_present = em5.find(blob) >= 0
    print(f'\nSaturation gain data ({len(blob)} bytes) present in E-M5 II:', gains_present)

    # The findings these numbers back. Fail loudly if they stop holding.
    checks = [
        ('ISP writer is a near-exact twin', results['ISP writer'] > 0.95),
        ('COLOR builder has no close twin', results['COLOR builder'] < 0.10),
        ('wheel drawing has no twin', results['Draw_C3d_Async'] == 0),
        ('gain data is absent', not gains_present),
    ]
    failed = [text for text, ok in checks if not ok]
    for text, ok in checks:
        print('ok  ' if ok else 'FAIL', text)
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
