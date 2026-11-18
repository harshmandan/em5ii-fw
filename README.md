# em5ii-fw

Research into adding COLOR profiles (the 12-sector colour wheel of the PEN-F and
OM-3) to the Olympus OM-D E-M5 Mark II, firmware 4.1.

**Status: research only.** Nothing here has been flashed to a camera. No patch
exists yet.

- [Findings](docs/FINDINGS.md): what the E-M5 II firmware already has and what is missing.
- [Roadmap](docs/ROADMAP.md): the staged plan.

## Warning

Writing modified firmware to a camera can brick it. This repository holds no
firmware and no flashable file. Treat every address here as specific to the
exact build named next to it.

## Setup

Python 3.12 or newer. No packages needed for the scans.

The work leans on two upstream projects. Clone them next to this README. They
are git-ignored, not vendored.

| Project | Commit used |
| --- | --- |
| [fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis) | `d565cb664d3bc37f883f844a3a0c9620efe018e4` |
| [flatpanda/om-emu](https://github.com/flatpanda/om-emu) | `750ad39fec02157897c09e1c520f042d95fdae4e` |

```bash
git clone https://github.com/fishcu/oly_fw_analysis.git
git clone https://github.com/flatpanda/om-emu.git
```

## Firmware inputs

Download the stock files from OM System's update server and decode them. Both
steps use upstream tools. Check the hashes: a matching version label is not enough.

| Body | File | SHA-256 |
| --- | --- | --- |
| E-M5 II 4.1 (build 4100) | `OLY_E_118_4100_0000_0000.BIN` | `c03050db130b051e446fa08dec1ad6f29afc890308888383428f4938a57edef0` |
| PEN-F 3.1 (build 3101) | `OLY_E_122_3101_0000_0000.BIN` | `77398610b379f80238117f31a6d5bbf65d608b49ec563666c64d84367e969f2c` |

```bash
cd oly_fw_analysis
python3 tools/om_firmware_catalog.py --model-id 1180 --model-name "E-M5 Mark II" --out ../fw/catalog --download
python3 tools/om_firmware_catalog.py --model-id 1220 --model-name PEN-F --out ../fw/catalog-penf --download
cd ..
python3 oly_fw_analysis/tools/oly_container.py fw/catalog/OLY_E_118_4100_0000_0000.BIN \
  --expect-sha256 c03050db130b051e446fa08dec1ad6f29afc890308888383428f4938a57edef0 \
  --code-base 0x60021020 --out fw/em5ii_4.1
python3 oly_fw_analysis/tools/oly_container.py fw/catalog-penf/OLY_E_122_3101_0000_0000.BIN \
  --expect-sha256 77398610b379f80238117f31a6d5bbf65d608b49ec563666c64d84367e969f2c \
  --code-base 0x60021020 --out fw/penf_3.1
```

The decoded main blocks must hash to:

| Body | Decoded main | SHA-256 |
| --- | --- | --- |
| E-M5 II | `fw/em5ii_4.1/00_0100_40300020.decoded.bin` | `ecd9603c4a264a358d91ef110a05f9236055e6369399f7c7de5985b21a2fd96a` |
| PEN-F | `fw/penf_3.1/00_0100_403a0020.decoded.bin` | `a2eb1d1f1afe47cce148e9aae0a04dfb82547d9de9437d342e012341140913f4` |

## Reproduce the findings

```bash
python3 tools/find_color_table.py
python3 tools/match_penf_code.py
```

Each script checks its input hashes first and exits non-zero if a finding in
[docs/FINDINGS.md](docs/FINDINGS.md) no longer holds.

## Credits

The PEN-F function map, the table layout and the container tools come from
fishcu/oly_fw_analysis. The emulator is flatpanda/om-emu. The idea follows
[androidfanman/caduceus-om3](https://github.com/androidfanman/caduceus-om3).
The firmware belongs to its vendor. This project is not affiliated with Olympus
or OM Digital Solutions.
