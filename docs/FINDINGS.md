# Findings

All addresses are CPU analysis addresses in the decoded main block, base
`0x60021020`. E-M5 II means firmware 4.1, build 4100. PEN-F means 3.1, build
3101. Exact file hashes are in the [README](../README.md).

## Evidence levels

| Tag | Meaning |
| --- | --- |
| **B** | Byte comparison of stock files. Reproduced by a script in `tools/`. |
| **R** | Read from upstream documentation. Not re-checked here. |
| **I** | Inference from B and R. Not yet confirmed by disassembly. |

Nothing below was run in an emulator or on a camera.

## 1. Feasibility check (2026-11-18)

Question: does the E-M5 II have the 12-sector colour pipeline that the PEN-F
uses for COLOR profiles, or must it be built from nothing?

Answer: the data and the hardware path are there. The code that turns twelve
saturation values into a profile is not. The editor screen is mostly not.

### 1.1 The COLOR table is present and unused

`tools/find_color_table.py`

- The 3,028-byte COLOR table is at `0x60620f14`. It is byte-identical to the
  table on PEN-F (`0x60622d74`), E-P7 and OM-3. (B)
- It occurs once, in the main block only. (B)
- It sits in a run of tables of the same size. The five tables before it are
  each referenced from a pointer array at `0x6062de60`, stride `0x34`. The
  table after it is referenced from code at `0x604df314`. (B)
- No 32-bit pointer anywhere in the main block refers to the COLOR table. (B)
- The table after COLOR is identical on both bodies. (B)

| Slot | Address | Referenced from |
| ---: | --- | --- |
| −5 | `0x6061d3f0` | `0x6062de60`, `0x6062de94` |
| −4 | `0x6061dfc4` | `0x6062dec8` |
| −3 | `0x6061eb98` | `0x6062defc` |
| −2 | `0x6061f76c` | `0x6062df30` |
| −1 | `0x60620340` | `0x6062df64` |
| 0 | `0x60620f14` | nothing (COLOR) |
| +1 | `0x60621ae8` | `0x604df314` |

On the PEN-F the table before COLOR is Bleach Bypass II. (R) Slot −1 is then
likely the same art filter here. (I)

The PEN-F selector loads the COLOR table with an immediate at `0x604f7502`. (B)
The E-M5 II has no such load, so its selector has no COLOR case. (I)

### 1.2 The hardware path is the same

`tools/match_penf_code.py`

The PEN-F routine that writes the twelve records and LUTs to the image
processor has a near-exact twin at `0x6049d252`: 459 of 462 ten-byte windows
match at one displacement. (B)

The art filters use tables of this same layout. (B, by the pointer array above)
So the 12-sector hardware is exercised by stock firmware on this body. (I)

### 1.3 The profile builder is missing

| PEN-F piece | PEN-F address | Windows matched | Reading |
| --- | --- | ---: | --- |
| ISP writer | `0x604b5006` | 459 / 462 | Twin at `0x6049d252` |
| Table selector | `0x604f747f` | 79 / 233 | Partial twin near `0x604df20f` |
| COLOR builder | `0x604f7272` | 15 / 494 | No close twin |
| Saturation gain data | via `0x6062fef8` | absent | 40 bytes, not found |

The builder is about 500 bytes on the PEN-F. It scales twelve saturation
values by per-sector gains and fills the table records. (R) It and its gain
data must be added. (I)

### 1.4 The editor is mostly missing

| PEN-F piece | PEN-F address | Windows matched |
| --- | --- | ---: |
| Editor local handler | `0x60cefd3d` | 105 / 758 |
| Editor state entry | `0x60cefa1d` | 56 / 758 |
| GUI setter | `0x607363b3` | 65 / 502 |
| Settings manager | `0x6075fbed` | 28 / 502 |
| COLOR up/down | `0x60cb0684` | 41 / 1014 |
| Wheel viewer constructor | `0x60c84664` | 26 / 659 |
| Wheel viewer update | `0x60c84901` | 4 / 758 |
| Wheel draw command | `0x6081b780` | 5 / 758 |
| `Draw_C3d_Async` | `0x60300b3d` | 0 / 502 |
| C3d value conversion | `0x602fc370` | 0 / 502 |

The generic property editor has partial twins. The wheel drawing code has
none. (B) The E-M5 II does have a Color Creator wheel, so it draws a wheel some
other way. Where is not yet known.

Spans for the editor rows are fixed lengths from the entry point, not measured
function sizes. Low scores mean "no close twin", not "no equivalent code".

### 1.5 Modified 4.1 firmware has been built before

- A published stock/hack pair for E-M5 II 4100 changes 6 decoded main bytes:
  two video duration operands at offsets `534866` and `53486c`, and a focus
  stacking allowlist branch at `3f2ad5` (`0x60413af5`). Repairing the additive
  checksum reproduces the distributed file. (R, oly_fw_analysis
  `docs/features/HISTORICAL_HACKS.md`)
- azqeurio/om-c-firmware lists an aperture-ring patch for E-M5 II 4.1 with 13
  patch records and 2,616 changed bytes. (R, oly_fw_analysis
  `provenance/azqeurio-release.json`)

We have not found a first-hand report of the second one running on an E-M5 II.

### 1.6 Emulator support

om-emu runs E-M5 II 4.1 (code E118) through its PEN-F port: start, S1, S2 and
playback on the TFT and EVF, with the card file system native. (R) It does not
model the image processor, so it cannot show colour output. (R)

## Open questions

1. Where does the E-M5 II selector choose its table, and what is the smallest
   hook that adds a COLOR case?
2. Does the PEN-F builder depend on request-structure offsets that differ here?
   PEN-F uses saturation offset 1076, records 676, control 964. (R)
3. Which FF runs lie inside a loaded section and are safe for new code?
4. Where are Color Creator's wheel and settings on this body?
5. Is there a spare picture-mode slot, or must an existing one be reused?
