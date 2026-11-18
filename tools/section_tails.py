#!/usr/bin/env python3
"""List the loaded sections of the E-M5 II main block and the free tail of each.

A run of FF bytes is only usable for new code where the loader copies it into
RAM. The section table gives each section's start. The loaded end comes from
a separate switch in the loader, not from the next section's start, so most
of each FF run in the file is never loaded.
"""
import re
import struct
import sys

from common import BASE, load_main

SECTION_TABLE = 0x60026d24   # rows of (destination, flash source, destination)
END_SELECTOR = 0x600420cf    # switch of `mov imm32,d0` rows, one per section
SECTIONS = 8

EXPECTED_TAILS = {0: 940, 1: 1752, 2: 112, 3: 1120, 4: 1536, 5: 352}


def main():
    em5 = load_main('em5ii')

    starts = []
    for i in range(SECTIONS):
        dst, src, dst2 = struct.unpack_from('<3I', em5, SECTION_TABLE - BASE + i * 12)
        if dst != dst2 or src >> 24 not in (0x40, 0x41):
            sys.exit(f'section table row {i} is not as recorded')
        starts.append(dst)

    window = em5[END_SELECTOR - BASE:END_SELECTOR - BASE + 8 * SECTIONS]
    ends = [struct.unpack('<I', m)[0] for m in re.findall(rb'\xfc\xcc(....)', window, re.S)]
    if len(ends) != SECTIONS:
        sys.exit('end selector is not as recorded')

    print('section  loaded range              free tail (bytes, from)')
    ok = True
    for i, (start, end) in enumerate(zip(starts, ends)):
        body = em5[start - BASE:end - BASE]
        tail = len(body) - len(body.rstrip(b'\xff'))
        print(f'{i}        {start:#x}..{end:#x}   {tail:5d}  {end - tail:#x}')
        if i in EXPECTED_TAILS and tail != EXPECTED_TAILS[i]:
            ok = False
    if not ok:
        sys.exit('a tail differs from the recorded size')


if __name__ == '__main__':
    main()
