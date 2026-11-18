#!/usr/bin/env python3
"""Check the stage 0 claims about the picture-mode selector by bytes alone.

1. The E-M5 II selector's helpers are twins of the PEN-F ones.
2. The space between two of those helpers is exactly one COLOR builder
   shorter on the E-M5 II.
3. Picture mode 11 (COLOR on the PEN-F) is not a known mode on the E-M5 II.
4. The PEN-F COLOR builder is a leaf with one absolute reference.
5. The bytes at the planned hook site are as recorded.

No disassembler is needed. docs/FINDINGS.md section 2 has the listings.
"""
import struct
import sys

from common import BASE, load_main

# (name, PEN-F address, E-M5 II address, length, max differing bytes)
TWINS = [
    ('custom-table applier', 0x604f6d67, 0x604ded37, 0x1ab, 0),
    ('generic applier', 0x604f6f12, 0x604deee2, 0x360, 17),
    ('0xF00D case', 0x604f746a, 0x604df242, 0x15, 0),
]

PENF_BUILDER = (0x604f7272, 0x604f746a)
PENF_GAIN_POINTERS = 0x6062fef8

# Hash table of known picture modes: 64 slots of (mode id, handler).
EM5_MODE_TABLE = 0x6062eae0
COLOR_MODE = 11

# `mov (56,a2),d0` then `btst 0x64202e,d0`: first instructions of the
# not-0xF00D path, where PEN-F tests for mode 11 first.
EM5_HOOK = 0x604df2b6
EM5_HOOK_BYTES = bytes.fromhex('f80238' 'fcec2e206400')


def cut(data, start, length):
    return data[start - BASE:start - BASE + length]


def main():
    penf = load_main('penf')
    em5 = load_main('em5ii')
    ok = True

    def check(text, condition):
        nonlocal ok
        ok &= bool(condition)
        print('ok  ' if condition else 'FAIL', text)

    for name, p, e, length, limit in TWINS:
        differing = sum(x != y for x, y in zip(cut(penf, p, length), cut(em5, e, length)))
        check(f'{name}: {differing} of {length} bytes differ (limit {limit})',
              differing <= limit)

    # Generic applier end to 0xF00D case start: PEN-F holds the builder there.
    penf_gap = 0x604f746a - 0x604f6f12
    em5_gap = 0x604df242 - 0x604deee2
    builder_len = PENF_BUILDER[1] - PENF_BUILDER[0]
    check(f'layout gap differs by the builder length ({builder_len} bytes)',
          penf_gap - em5_gap == builder_len)

    modes = [struct.unpack_from('<I', em5, EM5_MODE_TABLE - BASE + i * 8)[0]
             for i in range(64)]
    modes = sorted(m for m in modes if m)
    print('E-M5 II picture modes below 0x100:', [m for m in modes if m < 0x100])
    check(f'{len(modes)} known modes, mode {COLOR_MODE} not among them',
          len(modes) == 59 and COLOR_MODE not in modes)

    builder = cut(penf, PENF_BUILDER[0], builder_len)
    pointer = struct.pack('<I', PENF_GAIN_POINTERS)
    # "Leaf" (no call instruction) was read from the objdump listing, not
    # checked here. The absolute-address scan below covers imm32 operands only.
    check('builder refers to the gain pointer table exactly once',
          builder.count(pointer) == 1)
    # imm32 operands follow a two-byte `fc xx` opcode. Requiring that prefix
    # drops chance hits that straddle two instructions.
    absolute = [i for i in range(2, len(builder) - 3)
                if builder[i - 2] == 0xfc
                and 0x60000000 <= struct.unpack_from('<I', builder, i)[0] < 0x62000000]
    check('builder has no other absolute address', len(absolute) == 1)
    check('builder ends in ret', builder[-3:] == bytes.fromhex('dff060'))

    check(f'hook site {EM5_HOOK:#x} holds the recorded bytes',
          cut(em5, EM5_HOOK, len(EM5_HOOK_BYTES)) == EM5_HOOK_BYTES)

    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
