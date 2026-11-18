#!/usr/bin/env python3
"""Check that the E-M5 II's SD update client and shared updater mirror the PEN-F's.

Byte checks only. The step-by-step comparison of the two updaters' compares,
calls and returns was done on objdump listings and is recorded in
docs/FINDINGS.md section 8; this script pins the facts that do not need a
disassembler.
"""
import struct
import sys

from common import BASE, load_main

TASK_ROW = 0x6003a128          # same address on both bodies
ROW = '<7I'                    # id, 0, 0, entry, priority, stack, 0
EXPECTED = {
    'penf': {'entry': 0x60b1cbb5, 'updater': (0x60b1d527, 0x60b1db27), 'model': 0x1220, 'pattern': b'E122????BIN'},
    'em5ii': {'entry': 0x60b5e53d, 'updater': (0x60b5eea6, 0x60b5f4a6), 'model': 0x1180, 'pattern': b'E118????BIN'},
}
PRECHECK = {'penf': 0x60b1ce0c, 'em5ii': 0x60b5e78f}


def main():
    ok = True

    def check(text, cond):
        nonlocal ok
        ok &= bool(cond)
        print('ok  ' if cond else 'FAIL', text)

    rows = {}
    for body, want in EXPECTED.items():
        data = load_main(body)
        row = struct.unpack_from(ROW, data, TASK_ROW - BASE)
        rows[body] = row
        check(f'{body}: task 95 at {TASK_ROW:#x} enters {want["entry"]:#x}',
              row[0] == 95 and row[3] == want['entry'])
        check(f'{body}: the SD file pattern {want["pattern"].decode()} and DCOLYMP are present',
              want['pattern'] in data and b'DCOLYMP' in data)

        # `cmp imm16,d0` is fa c8 lo hi. The updater tests the model code this way.
        lo, hi = want['updater']
        window = data[lo - BASE:hi - BASE]
        own = window.count(b'\xfa\xc8' + struct.pack('<H', want['model']))
        check(f'{body}: the shared updater compares against its model code {want["model"]:#x} eight times', own == 8)

        stub = data[PRECHECK[body] - BASE:PRECHECK[body] - BASE + 4]
        check(f'{body}: the SD pre-check stub is `clr d0; retf`', stub == bytes.fromhex('00de0000'))

    check('both bodies give the SD client the same priority and stack',
          rows['penf'][4:6] == rows['em5ii'][4:6] == (45, 0x800))

    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
