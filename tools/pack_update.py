#!/usr/bin/env python3
"""Pack the stage 1 main block into SD update files for the E-M5 II.

Writes, under generated/stage1/:

    install/DCOLYMP/E1189999.BIN         patched main block only
    restore-stock/DCOLYMP/E1189999.BIN   stock main block only
    install-full/DCOLYMP/E1189999.BIN    all four blocks, main patched
    pack.json                            hashes and what was checked

The full variant is the stock update file with only the main block replaced.
It is the layout om-emu accepts for `--main`, and the layout of the one
published modified file for this body. Its stock counterpart is the vendor's
own update file, so no separate full restore file is written.

READ THIS FIRST. Installing either file writes the camera's main firmware.
A bad write, or code that fails at start-up, can leave the camera unable to
boot, and no recovery route is established for this body. Nothing here has
been installed on a camera. The checks below are about the file format only.
They say nothing about whether the patched code is safe to run.

What is checked:
  - the stock update file parses, every component checksum holds, and
    rebuilding it from its parts gives the same bytes back;
  - the patched main differs from stock only in the ranges build.json lists;
  - the packed file parses again with a valid checksum, the same component
    header, and a payload equal to the patched main.

What is assumed, from oly_fw_analysis's PEN-F work and not shown for this body:
  - that the camera accepts a main-only file of the same version;
  - that the SD updater is reached by a button held at power-on.

The container code is oly_fw_analysis's, imported from its checkout.
"""
import hashlib
import json
import sys
from pathlib import Path

from common import ROOT

sys.path.insert(0, str(ROOT / 'oly_fw_analysis/tools'))
try:
    from oly_container import parse, reconstruct, replace_payload
except ImportError:
    sys.exit('oly_fw_analysis checkout is missing. See "Setup" in README.md.')

STOCK = ROOT / 'fw/catalog/OLY_E_118_4100_0000_0000.BIN'
STOCK_SHA = 'c03050db130b051e446fa08dec1ad6f29afc890308888383428f4938a57edef0'
BUILD = ROOT / 'generated/stage1'
NAME = 'E1189999.BIN'   # the firmware's SD client matches DCOLYMP/E118????.BIN


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        sys.exit(f'pack_update: {message}')


def main():
    stock = STOCK.read_bytes()
    require(sha(stock) == STOCK_SHA, 'stock update file is not the expected build')
    blocks = parse(stock)            # validates wrappers and additive checksums
    require(reconstruct(blocks) == stock, 'stock file does not rebuild byte for byte')
    main_block = blocks[0]
    require(main_block.kind == 0x100, 'first component is not the main block')

    report = json.loads((BUILD / 'build.json').read_text())
    patched = (BUILD / 'main.bin').read_bytes()
    require(sha(main_block.payload) == report['stock_main_sha256'], 'build.json is for another stock main')
    require(sha(patched) == report['patched_main_sha256'], 'main.bin does not match build.json')
    require(len(patched) == len(main_block.payload), 'patched main changed size')

    # Every differing byte must lie inside a range the build declared.
    base = 0x60021020
    allowed = [(int(r['start'], 16) - base, int(r['start'], 16) - base + r['bytes']) for r in report['ranges']]
    changed = [i for i, (a, b) in enumerate(zip(patched, main_block.payload)) if a != b]
    require(changed and all(any(lo <= i < hi for lo, hi in allowed) for i in changed),
            'patched main differs outside the declared ranges')

    new_block = replace_payload(main_block, patched)
    install = reconstruct([new_block])
    restore = reconstruct([main_block])

    back = parse(install)
    require(len(back) == 1 and back[0].payload == patched, 'packed file does not parse back to the patched main')
    require(back[0].header == main_block.header and back[0].trailer[:28] == main_block.trailer[:28],
            'component metadata changed')
    require(parse(restore)[0].payload == main_block.payload, 'restore file does not hold the stock main')
    require(restore == stock[:len(restore)], 'restore file is not the leading part of the stock update file')

    full = reconstruct([new_block] + blocks[1:])
    back_full = parse(full)
    require(len(full) == len(stock) and back_full[0].payload == patched, 'full file does not hold the patched main')
    require(all(a.payload == b.payload and a.header == b.header and a.trailer == b.trailer
                for a, b in zip(back_full[1:], blocks[1:])), 'full file changed another component')
    end = main_block.offset + 32 + len(main_block.payload) + 32
    require(full[end:] == stock[end:], 'full file differs from stock after the main component')

    for folder, data in (('install', install), ('restore-stock', restore), ('install-full', full)):
        target = BUILD / folder / 'DCOLYMP' / NAME
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    out = {
        'installed_on_a_camera': False,
        'carrier_mode': report['carrier_mode'],
        'look': report['look'],
        'changed_main_bytes': len(changed),
        'install': {'path': f'install/DCOLYMP/{NAME}', 'bytes': len(install), 'sha256': sha(install)},
        'restore_stock': {'path': f'restore-stock/DCOLYMP/{NAME}', 'bytes': len(restore), 'sha256': sha(restore)},
        'install_full': {'path': f'install-full/DCOLYMP/{NAME}', 'bytes': len(full), 'sha256': sha(full),
                         'restore': 'the stock update file itself, sha256 ' + STOCK_SHA},
        'checked': ['stock file rebuilds byte for byte', 'changes lie inside declared ranges',
                    'packed file parses with a valid checksum and unchanged metadata',
                    'restore file equals the head of the stock update file',
                    'full file equals stock outside the main component'],
        'assumed': ['a main-only file of the same version is accepted',
                    'the SD updater is reached by a button held at power-on'],
    }
    (BUILD / 'pack.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
