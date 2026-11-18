#!/usr/bin/env python3
"""Build the stage 1 patch as a patched main block for the emulator.

Output: generated/stage1/main.bin (a decoded main block, for om-emu's
`--main`) and generated/stage1/build.json. This does NOT produce a file a
camera can install. Repacking into an update container is a separate,
deliberate step that does not exist yet.

The COLOR builder and its gain data are not in this repository. They are
read from your own PEN-F 3.1 firmware at build time and checked by hash.
"""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

from common import BASE, ROOT, load_main

SRC = ROOT / 'patches/stage1'
OUT = ROOT / 'generated/stage1'
BINUTILS = ROOT / 'toolchains/build'

# ---- E-M5 II 4100 ---------------------------------------------------------
COLOR_TABLE = 0x60620f14
HOOK = 0x604df2b6
HOOK_STOCK = bytes.fromhex('f80238' 'fcec2e206400')
RESUME_STOCK = 0x604df2bf        # the beq after the displaced btst
EXIT_CACHE_TAG = 0x604df2a6      # add 52,a2; tag check; ret
EXIT_CLEAR_DIRTY = 0x604df2f5    # add 100,a2; clear bit 4; ret

# Section 1 as the loader copies it, and its FF tail (FINDINGS section 3).
SECTION = (0x60218000, 0x603f8800)
TAIL_START = 0x603f8128
PATCH_BASE = 0x603f8140

# ---- PEN-F 3101 -----------------------------------------------------------
PENF_BUILDER = (0x604f7272, 0x604f746a)
PENF_GAIN_POINTERS = 0x6062fef8

# Layout inside the patch, offsets from PATCH_BASE.
OFF_SAT = 0          # 12 signed bytes, padded to 16
OFF_GAIN_POINTERS = 16   # 12 pointers
OFF_GAIN_DATA = 64       # 40 bytes
OFF_BUILDER = 104        # 504 bytes
OFF_STUB = 608


def cut(data, start, stop):
    return data[start - BASE:stop - BASE]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tool(name):
    path = BINUTILS / name
    if not path.exists():
        sys.exit(f'{path} is missing. See "Toolchain" in README.md.')
    return str(path)


def assemble_stub(symbols, stub_address):
    OUT.mkdir(parents=True, exist_ok=True)
    obj, elf, raw = OUT / 'stub.o', OUT / 'stub.elf', OUT / 'stub.bin'
    defs = [f'--defsym={k}={v:#x}' for k, v in symbols.items()]
    # The symbols are resolved by the linker, not the assembler. Given to the
    # assembler they become plain constants, and a branch to one is then
    # emitted without subtracting the instruction's address.
    subprocess.check_call([tool('gas/as-new'), '-o', str(obj), str(SRC / 'stub.s')])
    subprocess.check_call([tool('ld/ld-new'), '-e', 'stub', f'-Ttext={stub_address:#x}',
                           *defs, '-o', str(elf), str(obj)])
    subprocess.check_call([tool('binutils/objcopy'), '-O', 'binary', '-j', '.text',
                           str(elf), str(raw)])
    return raw.read_bytes()


def hook_bytes(target):
    # `jmp (d32,pc)` is dc + rel32, relative to the instruction's own address.
    jump = b'\xdc' + struct.pack('<i', target - HOOK)
    return jump + b'\xcb' * (len(HOOK_STOCK) - len(jump))  # nop


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--carrier-mode', type=lambda s: int(s, 0), required=True,
                    help='picture mode number that carries the look')
    ap.add_argument('--look', type=Path, default=SRC / 'look.json')
    args = ap.parse_args()

    penf = load_main('penf')
    em5 = bytearray(load_main('em5ii'))

    look = json.loads(args.look.read_text())
    sat = look['saturation']
    if len(sat) != 12 or any(not isinstance(v, int) or not -5 <= v <= 5 for v in sat):
        sys.exit('look: need twelve integers from -5 to 5')

    # Parts taken from the PEN-F file.
    builder = bytearray(cut(penf, *PENF_BUILDER))
    pointers = struct.unpack_from('<12I', penf, PENF_GAIN_POINTERS - BASE)
    lo = min(pointers)
    gain_data = cut(penf, lo, max(pointers) + 4)
    assert len(builder) == 504 and len(gain_data) == 40

    # Repoint the builder's one absolute reference at our pointer table.
    old = struct.pack('<I', PENF_GAIN_POINTERS)
    assert builder.count(old) == 1
    at = builder.index(old)
    builder[at:at + 4] = struct.pack('<I', PATCH_BASE + OFF_GAIN_POINTERS)
    new_pointers = struct.pack('<12I', *(PATCH_BASE + OFF_GAIN_DATA + p - lo for p in pointers))

    stub = assemble_stub({
        'CARRIER_MODE': args.carrier_mode,
        'COLOR_TABLE': COLOR_TABLE,
        'SAT_VALUES': PATCH_BASE + OFF_SAT,
        'BUILDER': PATCH_BASE + OFF_BUILDER,
        'RESUME_STOCK': RESUME_STOCK,
        'EXIT_CACHE_TAG': EXIT_CACHE_TAG,
        'EXIT_CLEAR_DIRTY': EXIT_CLEAR_DIRTY,
    }, PATCH_BASE + OFF_STUB)

    blob = bytearray(b'\xff' * OFF_STUB) + stub
    blob[OFF_SAT:OFF_SAT + 12] = struct.pack('<12b', *sat)
    blob[OFF_GAIN_POINTERS:OFF_GAIN_POINTERS + 48] = new_pointers
    blob[OFF_GAIN_DATA:OFF_GAIN_DATA + 40] = gain_data
    blob[OFF_BUILDER:OFF_BUILDER + 504] = builder
    end = PATCH_BASE + len(blob)

    # Placement checks: inside the loaded tail, on bytes that are FF in stock.
    assert TAIL_START <= PATCH_BASE and end <= SECTION[1], 'patch leaves the loaded tail'
    assert set(cut(em5, PATCH_BASE, end)) == {0xff}, 'target bytes are not free'
    assert cut(em5, HOOK, HOOK + len(HOOK_STOCK)) == HOOK_STOCK, 'hook site differs'
    assert sha(cut(em5, COLOR_TABLE, COLOR_TABLE + 3028)) == \
        'a33d64bdb78ac41ba24ccbff820380f563211a095ac08a12a7c37a51b5c00531'

    stock_sha = sha(em5)
    em5[PATCH_BASE - BASE:end - BASE] = blob
    em5[HOOK - BASE:HOOK - BASE + len(HOOK_STOCK)] = hook_bytes(PATCH_BASE + OFF_STUB)

    (OUT / 'main.bin').write_bytes(em5)
    report = {
        'target': 'E-M5 II 4.1 (4100), decoded main block',
        'flashable': False,
        'carrier_mode': args.carrier_mode,
        'look': look['name'],
        'saturation': sat,
        'stock_main_sha256': stock_sha,
        'patched_main_sha256': sha(em5),
        'ranges': [
            {'what': 'hook', 'start': hex(HOOK), 'bytes': len(HOOK_STOCK)},
            {'what': 'patch', 'start': hex(PATCH_BASE), 'bytes': len(blob)},
        ],
        'layout': {
            'saturation': hex(PATCH_BASE + OFF_SAT),
            'gain_pointers': hex(PATCH_BASE + OFF_GAIN_POINTERS),
            'gain_data': hex(PATCH_BASE + OFF_GAIN_DATA),
            'builder': hex(PATCH_BASE + OFF_BUILDER),
            'stub': hex(PATCH_BASE + OFF_STUB),
            'end': hex(end),
        },
        'tail_bytes_left': SECTION[1] - end,
    }
    (OUT / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
